"""Read-only parent planner visibility — real schedule slot data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planner import PlannerScheduleSlot, ScheduleSlotStatus
from app.models.student_activity_tracking import EngagementEventType, StudentEngagementEvent
from app.services.planner_intelligence_service import (
    AR_WEEKDAYS,
    enrich_slot,
    get_planner_visibility_snapshot,
)
from app.services.student_performance_analytics_service import compute_subject_analytics

STATUS_LABELS = {
    "completed": ("مكتمل", "check"),
    "planned": ("قيد الانتظار", "pending"),
    "missed": ("فائت", "missed"),
    "overdue": ("متأخر", "overdue"),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


async def _completion_times(
    db: AsyncSession, student_id: int, slot_ids: list[int]
) -> dict[int, datetime]:
    if not slot_ids:
        return {}
    result = await db.execute(
        select(StudentEngagementEvent.resource_id, StudentEngagementEvent.occurred_at)
        .where(
            StudentEngagementEvent.student_id == student_id,
            StudentEngagementEvent.event_type == EngagementEventType.planner_activity,
            StudentEngagementEvent.resource_type == "planner_slot",
            StudentEngagementEvent.resource_id.in_(slot_ids),
        )
        .order_by(StudentEngagementEvent.occurred_at.asc())
    )
    out: dict[int, datetime] = {}
    for slot_id, occurred_at in result.all():
        if slot_id is not None and occurred_at:
            out[int(slot_id)] = occurred_at
    return out


def _effective_status(slot: PlannerScheduleSlot, now: datetime) -> str:
    status = slot.status.value if hasattr(slot.status, "value") else str(slot.status)
    if status == ScheduleSlotStatus.planned.value and slot.scheduled_at < now:
        return "overdue"
    return status


def _task_out(
    slot: PlannerScheduleSlot,
    enriched: dict,
    *,
    completion_at: datetime | None,
    now: datetime,
) -> dict:
    eff = _effective_status(slot, now)
    label, icon = STATUS_LABELS.get(eff, ("—", "pending"))
    return {
        "id": slot.id,
        "subject": slot.subject,
        "task_name": enriched.get("task_label") or slot.subject,
        "planned_at": _iso(slot.scheduled_at),
        "completed_at": _iso(completion_at) if eff == "completed" else None,
        "status": eff,
        "status_label": label,
        "status_icon": icon,
        "duration_minutes": int(slot.duration_minutes or 0),
        "is_overdue": eff == "overdue",
    }


def _week_start(d: datetime) -> datetime:
    return (d - timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


async def build_parent_planner_visibility(db: AsyncSession, student_id: int) -> dict:
    now = _utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    week_start = _week_start(now)
    week_end = week_start + timedelta(days=7)
    lookback = now - timedelta(days=7)

    analytics = await compute_subject_analytics(db, student_id)
    analytics_map = {p.subject_name: p for p in analytics}

    result = await db.execute(
        select(PlannerScheduleSlot)
        .where(
            PlannerScheduleSlot.student_id == student_id,
            PlannerScheduleSlot.scheduled_at >= lookback,
            PlannerScheduleSlot.scheduled_at < week_end + timedelta(days=7),
        )
        .order_by(PlannerScheduleSlot.scheduled_at)
    )
    slots = list(result.scalars().all())
    completion_map = await _completion_times(db, student_id, [s.id for s in slots])

    today_plan: list[dict] = []
    upcoming: list[dict] = []
    completed: list[dict] = []
    missed: list[dict] = []
    overdue: list[dict] = []
    timeline: list[dict] = []
    by_day: dict[str, dict] = {}

    week_due_completed = 0
    week_due_missed = 0
    week_due_overdue = 0
    week_due_pending = 0
    subject_stats: dict[str, dict] = {}
    active_days: set = set()

    for slot in slots:
        enriched = enrich_slot(slot, analytics_map)
        task = _task_out(slot, enriched, completion_at=completion_map.get(slot.id), now=now)
        timeline.append(task)

        eff = task["status"]
        in_week = week_start <= slot.scheduled_at < week_end

        if today_start <= slot.scheduled_at < today_end:
            today_plan.append(task)

        if eff == "completed":
            completed.append(task)
            if in_week:
                week_due_completed += 1
                active_days.add(slot.scheduled_at.date())
        elif eff == "missed":
            missed.append(task)
            if in_week:
                week_due_missed += 1
        elif eff == "overdue":
            overdue.append(task)
            if in_week:
                week_due_overdue += 1
        elif slot.scheduled_at >= now:
            upcoming.append(task)
            if in_week:
                week_due_pending += 1

        if in_week and eff in ("completed", "missed", "overdue"):
            subj = slot.subject
            bucket = subject_stats.setdefault(subj, {"completed": 0, "total": 0})
            bucket["total"] += 1
            if eff == "completed":
                bucket["completed"] += 1

        day_date = slot.scheduled_at.date()
        if week_start.date() <= day_date < week_end.date():
            day_name = AR_WEEKDAYS[slot.scheduled_at.weekday()]
            key = day_date.isoformat()
            if key not in by_day:
                by_day[key] = {"day_name": day_name, "date": key, "tasks": []}
            by_day[key]["tasks"].append(task)

    weekly_plan = sorted(by_day.values(), key=lambda d: d["date"])
    timeline.sort(key=lambda t: t.get("planned_at") or "", reverse=True)

    total_due = week_due_completed + week_due_missed + week_due_overdue
    adherence = int(round((week_due_completed / total_due) * 100)) if total_due else 0

    subject_breakdown = []
    for name, stats in sorted(subject_stats.items(), key=lambda x: x[0]):
        total = stats["total"]
        done = stats["completed"]
        pct = int(round((done / total) * 100)) if total else 0
        subject_breakdown.append(
            {
                "subject_name": name,
                "adherence_percent": pct,
                "completed_count": done,
                "total_count": total,
            }
        )

    active_day_count = len(active_days)
    consistency_label = f"{active_day_count} / 7 أيام"

    snap = await get_planner_visibility_snapshot(db, student_id)
    stats = snap.get("plan_stats") or {}

    return {
        "summary": snap.get("summary", ""),
        "plan_active": bool(slots) or stats.get("planned_count", 0) > 0,
        "today_plan": today_plan,
        "weekly_plan": weekly_plan,
        "upcoming_tasks": upcoming[:12],
        "completed_tasks": completed[:12],
        "missed_tasks": missed[:12],
        "overdue_tasks": overdue[:12],
        "task_timeline": timeline[:24],
        "commitment": {
            "adherence_rate": adherence,
            "completed_count": week_due_completed,
            "total_due_count": total_due,
            "missed_count": week_due_missed,
            "pending_count": week_due_pending,
            "overdue_count": week_due_overdue,
        },
        "subject_breakdown": subject_breakdown,
        "weekly_consistency": {
            "active_days": active_day_count,
            "total_days": 7,
            "label": consistency_label,
        },
        "streak": snap.get("streak") or {},
        "recommendations": snap.get("recommendations") or [],
        "subject_analytics": snap.get("subject_analytics") or [],
        "upcoming": [t for t in upcoming[:8]],
        "weekly_plan_legacy": snap.get("weekly_plan") or [],
        "plan_stats": {
            **stats,
            "adherence_rate": adherence,
            "completed_count": week_due_completed,
            "missed_count": week_due_missed,
            "overdue_count": week_due_overdue,
        },
        "completed_total": week_due_completed,
    }


async def get_planner_adherence_for_ai(db: AsyncSession, student_id: int) -> dict:
    """Compact planner analytics for AI executive summary."""
    data = await build_parent_planner_visibility(db, student_id)
    c = data.get("commitment") or {}
    return {
        "adherence_rate": c.get("adherence_rate", 0),
        "completed_tasks": c.get("completed_count", 0),
        "total_due_tasks": c.get("total_due_count", 0),
        "missed_tasks": c.get("missed_count", 0),
        "pending_tasks": c.get("pending_count", 0),
        "overdue_tasks": c.get("overdue_count", 0),
        "weekly_consistency_days": (data.get("weekly_consistency") or {}).get("active_days", 0),
        "subject_breakdown": data.get("subject_breakdown") or [],
    }
