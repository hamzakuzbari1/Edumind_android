"""Data-driven planner: weekly plans, priorities, recommendations, streaks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planner import (
    LifeEventType,
    PlannerLifeEvent,
    PlannerScheduleSlot,
    ScheduleSlotStatus,
)
from app.services.planner_chat_service import get_planner_state, _slot_out, _event_out
from app.services.planner_memory_service import get_or_create_profile, profile_to_dict
from app.services.planner_streak_service import get_or_create_streak, streak_to_dict
from app.services.schedule_optimizer import optimize_schedule
from app.services.student_performance_analytics_service import (
    STRENGTH_WEAK,
    SubjectPerformance,
    compute_subject_analytics,
    sync_profile_weak_subjects,
    weak_subject_names,
)

AR_WEEKDAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

PRIORITY_LABEL_AR = {
    PRIORITY_HIGH: "أولوية عالية",
    PRIORITY_MEDIUM: "أولوية متوسطة",
    PRIORITY_LOW: "أولوية منخفضة",
}

PRIORITY_ICON = {
    PRIORITY_HIGH: "🔥",
    PRIORITY_MEDIUM: "⚠️",
    PRIORITY_LOW: "✅",
}


def priority_tier(slot_priority: int) -> str:
    if slot_priority >= 8:
        return PRIORITY_HIGH
    if slot_priority >= 4:
        return PRIORITY_MEDIUM
    return PRIORITY_LOW


def _task_label(slot: PlannerScheduleSlot | dict, analytics_map: dict[str, SubjectPerformance]) -> str:
    subject = slot.subject if hasattr(slot, "subject") else slot.get("subject", "")
    minutes = slot.duration_minutes if hasattr(slot, "duration_minutes") else slot.get("duration_minutes", 45)
    reasoning = slot.reasoning if hasattr(slot, "reasoning") else slot.get("reasoning") or ""
    if "امتحان" in reasoning or "قرب الامتحان" in reasoning:
        return f"مراجعة {subject} قبل الامتحان — {minutes} دقيقة"
    if "مادة ضعيفة" in reasoning:
        return f"{subject} — تركيز على نقاط الضعف ({minutes} دقيقة)"
    perf = analytics_map.get(subject)
    if perf and perf.missed_lessons > 0:
        return f"إكمال دروس {subject} ({minutes} دقيقة)"
    return f"{subject} — {minutes} دقيقة"


def enrich_slot(slot: PlannerScheduleSlot, analytics_map: dict[str, SubjectPerformance]) -> dict:
    base = _slot_out(slot)
    tier = priority_tier(slot.priority)
    base["priority_tier"] = tier
    base["priority_label"] = PRIORITY_LABEL_AR[tier]
    base["priority_icon"] = PRIORITY_ICON[tier]
    base["task_label"] = _task_label(slot, analytics_map)
    return base


def _slot_status(slot) -> str:
    if hasattr(slot, "status"):
        s = slot.status
        return s.value if hasattr(s, "value") else str(s)
    return slot.get("status", "planned")


def build_weekly_plan(slots: list, analytics_map: dict[str, SubjectPerformance]) -> list[dict]:
    """Group enriched slots by Arabic weekday for the next 7 days."""
    now = datetime.now(timezone.utc)
    week_end = now + timedelta(days=7)
    by_day: dict[str, list] = {}

    for slot in slots:
        at = slot.scheduled_at if hasattr(slot, "scheduled_at") else slot.get("scheduled_at")
        if isinstance(at, str):
            at = datetime.fromisoformat(at.replace("Z", "+00:00"))
        if at < now or at > week_end:
            continue
        if hasattr(slot, "status"):
            status = _slot_status(slot)
        else:
            status = slot.get("status")
        if status != "planned":
            continue
        day_name = AR_WEEKDAYS[at.weekday()]
        enriched = enrich_slot(slot, analytics_map) if hasattr(slot, "subject") else slot
        by_day.setdefault(day_name, []).append(enriched)

    order = []
    seen = set()
    for offset in range(7):
        day_dt = now + timedelta(days=offset)
        name = AR_WEEKDAYS[day_dt.weekday()]
        if name in seen:
            continue
        seen.add(name)
        tasks = sorted(by_day.get(name, []), key=lambda t: t.get("scheduled_at", ""))
        if tasks:
            order.append({"day_name": name, "day_offset": offset, "tasks": tasks})

    return order


def build_recommendations(
    analytics: list[SubjectPerformance],
    slots: list[PlannerScheduleSlot],
    life_events: list[PlannerLifeEvent],
) -> list[dict]:
    recs: list[dict] = []
    exams = [e for e in life_events if e.event_type == LifeEventType.exam]

    for ex in exams[:2]:
        subj = ex.subject or ex.title
        recs.append(
            {
                "text": f"ركّز على {subj} قبل {ex.title or 'الامتحان'} القادم",
                "priority_tier": PRIORITY_HIGH,
                "priority_label": PRIORITY_LABEL_AR[PRIORITY_HIGH],
                "priority_icon": PRIORITY_ICON[PRIORITY_HIGH],
                "subject": subj,
            }
        )

    for perf in analytics:
        if perf.strength_level != STRENGTH_WEAK:
            continue
        if perf.completion_percent < 50 and perf.missed_lessons > 0:
            recs.append(
                {
                    "text": f"مستواك منخفض في {perf.subject_name} — يوصى بمراجعة الدروس المتبقية ({perf.missed_lessons} درس)",
                    "priority_tier": PRIORITY_HIGH,
                    "priority_label": PRIORITY_LABEL_AR[PRIORITY_HIGH],
                    "priority_icon": PRIORITY_ICON[PRIORITY_HIGH],
                    "subject": perf.subject_name,
                }
            )
        elif perf.average_score < 60:
            recs.append(
                {
                    "text": f"متوسط درجاتك في {perf.subject_name} {perf.average_score}% — خصص وقتاً إضافياً للمراجعة",
                    "priority_tier": PRIORITY_MEDIUM,
                    "priority_label": PRIORITY_LABEL_AR[PRIORITY_MEDIUM],
                    "priority_icon": PRIORITY_ICON[PRIORITY_MEDIUM],
                    "subject": perf.subject_name,
                }
            )

    for perf in analytics:
        if perf.completion_percent >= 90 and perf.strength_level != STRENGTH_WEAK:
            recs.append(
                {
                    "text": f"أكملت {perf.completion_percent}% من {perf.subject_name} — استمر على هذا الإيقاع",
                    "priority_tier": PRIORITY_LOW,
                    "priority_label": PRIORITY_LABEL_AR[PRIORITY_LOW],
                    "priority_icon": PRIORITY_ICON[PRIORITY_LOW],
                    "subject": perf.subject_name,
                }
            )
            break

    upcoming = sorted(
        [s for s in slots if s.scheduled_at > datetime.now(timezone.utc)],
        key=lambda s: s.scheduled_at,
    )
    if upcoming and len(recs) < 6:
        nxt = upcoming[0]
        recs.append(
            {
                "text": f"المهمة القادمة: {nxt.subject} — {_task_label(nxt, {p.subject_name: p for p in analytics})}",
                "priority_tier": priority_tier(nxt.priority),
                "priority_label": PRIORITY_LABEL_AR[priority_tier(nxt.priority)],
                "priority_icon": PRIORITY_ICON[priority_tier(nxt.priority)],
                "subject": nxt.subject,
            }
        )

    return recs[:8]


def build_dashboard_snapshot(
    slots: list,
    analytics: list[SubjectPerformance],
    streak: dict,
    recommendations: list[dict],
) -> dict:
    now = datetime.now(timezone.utc)
    today_name = AR_WEEKDAYS[now.weekday()]
    today_tasks = []
    for slot in slots:
        at = slot.scheduled_at if hasattr(slot, "scheduled_at") else slot.get("scheduled_at")
        if isinstance(at, str):
            at = datetime.fromisoformat(at.replace("Z", "+00:00"))
        if at.date() == now.date():
            status = _slot_status(slot) if hasattr(slot, "status") else slot.get("status")
            if status == "planned":
                analytics_map = {p.subject_name: p for p in analytics}
                today_tasks.append(enrich_slot(slot, analytics_map) if hasattr(slot, "subject") else slot)

    weak = [a for a in analytics if a.strength_level == STRENGTH_WEAK]
    current_priority = None
    if weak:
        w = weak[0]
        current_priority = {
            "subject": w.subject_name,
            "reason": f"مادة ضعيفة — {w.average_score}% متوسط · {w.completion_percent}% إكمال",
            "priority_tier": PRIORITY_HIGH,
            "priority_icon": PRIORITY_ICON[PRIORITY_HIGH],
        }
    elif recommendations:
        r = recommendations[0]
        current_priority = {
            "subject": r.get("subject"),
            "reason": r["text"],
            "priority_tier": r["priority_tier"],
            "priority_icon": r["priority_icon"],
        }

    upcoming = sorted(
        [s for s in slots if (s.scheduled_at if hasattr(s, "scheduled_at") else s.get("scheduled_at")) > now],
        key=lambda s: s.scheduled_at if hasattr(s, "scheduled_at") else s.get("scheduled_at"),
    )
    next_task = None
    if upcoming:
        analytics_map = {p.subject_name: p for p in analytics}
        nxt = upcoming[0]
        next_task = enrich_slot(nxt, analytics_map) if hasattr(nxt, "subject") else nxt

    return {
        "today_tasks": today_tasks,
        "today_label": today_name,
        "current_priority": current_priority,
        "streak": streak,
        "next_task": next_task,
        "streak_display": f"🔥 سلسلة التعلم: {streak.get('current_streak_days', 0)} يوم",
    }


async def _count_planned_ahead(db: AsyncSession, student_id: int) -> int:
    now = datetime.now(timezone.utc)
    week_ahead = now + timedelta(days=7)
    result = await db.execute(
        select(PlannerScheduleSlot).where(
            PlannerScheduleSlot.student_id == student_id,
            PlannerScheduleSlot.status == ScheduleSlotStatus.planned,
            PlannerScheduleSlot.scheduled_at >= now,
            PlannerScheduleSlot.scheduled_at <= week_ahead,
        )
    )
    return len(list(result.scalars().all()))


async def generate_weekly_plan(db: AsyncSession, student_id: int) -> tuple[list[PlannerScheduleSlot], list[str]]:
    analytics = await compute_subject_analytics(db, student_id)
    profile = await get_or_create_profile(db, student_id)
    sync_profile_weak_subjects(profile, analytics)

    slots, reasoning = await optimize_schedule(db, student_id, profile, days=7)

    if analytics:
        weak = weak_subject_names(analytics)
        if weak:
            reasoning.insert(0, f"تحليل الأداء: تركيز على {', '.join(weak[:3])}")
        top = analytics[0]
        reasoning.append(
            f"إكمال {top.subject_name}: {top.completion_percent}% · متوسط الدرجات {top.average_score}%"
        )

    await db.flush()
    return slots, reasoning


async def get_enriched_planner_state(
    db: AsyncSession,
    student_id: int,
    *,
    auto_generate: bool = True,
) -> dict:
    if auto_generate and await _count_planned_ahead(db, student_id) < 2:
        await generate_weekly_plan(db, student_id)
        await db.commit()

    base = await get_planner_state(db, student_id)
    analytics = await compute_subject_analytics(db, student_id)
    analytics_map = {p.subject_name: p for p in analytics}

    slot_result = await db.execute(
        select(PlannerScheduleSlot)
        .where(PlannerScheduleSlot.student_id == student_id)
        .order_by(PlannerScheduleSlot.scheduled_at)
        .limit(80)
    )
    slot_rows = list(slot_result.scalars().all())

    ev_result = await db.execute(
        select(PlannerLifeEvent)
        .where(PlannerLifeEvent.student_id == student_id)
        .order_by(PlannerLifeEvent.event_date.asc().nullslast(), PlannerLifeEvent.created_at.desc())
    )
    life_events = list(ev_result.scalars().all())

    enriched_schedule = [enrich_slot(s, analytics_map) for s in slot_rows]
    weekly_plan = build_weekly_plan(slot_rows, analytics_map)
    recommendations = build_recommendations(analytics, slot_rows, life_events)

    streak_row = await get_or_create_streak(db, student_id)
    streak = streak_to_dict(streak_row)

    now = datetime.now(timezone.utc)
    week_start = now
    week_end = now + timedelta(days=7)
    completed = sum(
        1
        for s in slot_rows
        if s.status == ScheduleSlotStatus.completed
        and s.scheduled_at >= week_start - timedelta(days=7)
    )
    missed = sum(
        1
        for s in slot_rows
        if s.status == ScheduleSlotStatus.missed
        and s.scheduled_at >= week_start - timedelta(days=7)
    )
    planned_week = [s for s in slot_rows if week_start <= s.scheduled_at <= week_end]

    dashboard = build_dashboard_snapshot(slot_rows, analytics, streak, recommendations)

    return {
        **base,
        "schedule": enriched_schedule,
        "weekly_plan": weekly_plan,
        "subject_analytics": [p.to_dict() for p in analytics],
        "recommendations": recommendations,
        "streak": streak,
        "dashboard_snapshot": dashboard,
        "plan_stats": {
            "planned_count": len([s for s in planned_week if s.status == ScheduleSlotStatus.planned]),
            "completed_count": completed,
            "missed_count": missed,
        },
    }


async def get_planner_visibility_snapshot(db: AsyncSession, student_id: int) -> dict:
    """Read-only summary for parent/teacher dashboards."""
    state = await get_enriched_planner_state(db, student_id, auto_generate=False)
    return {
        "weekly_plan": state.get("weekly_plan", []),
        "subject_analytics": state.get("subject_analytics", []),
        "recommendations": state.get("recommendations", [])[:4],
        "streak": state.get("streak", {}),
        "plan_stats": state.get("plan_stats", {}),
        "upcoming": [
            s
            for s in state.get("schedule", [])
            if s.get("status") == "planned"
        ][:8],
        "completed_tasks": [
            s
            for s in state.get("schedule", [])
            if s.get("status") == "completed"
        ][:8],
        "missed_tasks": [
            s for s in state.get("schedule", []) if s.get("status") == "missed"
        ][:8],
        "summary": _visibility_summary(state),
    }


def _visibility_summary(state: dict) -> str:
    stats = state.get("plan_stats") or {}
    streak = state.get("streak") or {}
    planned = stats.get("planned_count", 0)
    done = stats.get("completed_count", 0)
    if planned == 0 and done == 0:
        return "لا توجد خطة نشطة حالياً"
    return f"خطة نشطة — {planned} مهام قادمة · {done} مكتملة · سلسلة {streak.get('current_streak_days', 0)} يوم"
