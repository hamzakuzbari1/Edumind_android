"""Historical parent reports — lessons, attendance, planner, grades over time."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planner import PlannerScheduleSlot, ScheduleSlotStatus
from app.models.progress import StudentLessonProgress
from app.models.quiz import QuizAttempt
from app.models.student_activity_tracking import StudentActivitySession
from app.models.user import User
from app.services.parent_attendance_analytics_service import (
    _daily_study_minutes,
    _day_label,
    _login_history,
    _month_end,
    _month_start,
    _pct_change,
    _range_dt,
    _sum_study_seconds,
    _week_start_sunday,
)
from app.services.parent_student_context_service import build_linked_child_context, grade_label

PERIOD_LABELS = {
    "this_week": "هذا الأسبوع",
    "last_week": "الأسبوع السابق",
    "this_month": "هذا الشهر",
    "last_month": "الشهر السابق",
    "custom": "فترة مخصصة",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def resolve_period(
    period: str,
    *,
    today: date | None = None,
    custom_start: date | None = None,
    custom_end: date | None = None,
) -> tuple[date, date, date, date, str, str]:
    """Return (start, end, prev_start, prev_end, period_label, prev_label)."""
    today = today or _utcnow().date()

    if period == "this_week":
        start = _week_start_sunday(today, offset=0)
        end = min(start + timedelta(days=6), today)
        prev_start = _week_start_sunday(today, offset=1)
        prev_end = prev_start + timedelta(days=6)
        return start, end, prev_start, prev_end, PERIOD_LABELS["this_week"], PERIOD_LABELS["last_week"]

    if period == "last_week":
        start = _week_start_sunday(today, offset=1)
        end = start + timedelta(days=6)
        prev_start = _week_start_sunday(today, offset=2)
        prev_end = prev_start + timedelta(days=6)
        return start, end, prev_start, prev_end, PERIOD_LABELS["last_week"], "الأسبوع قبل السابق"

    if period == "this_month":
        start = _month_start(today, offset=0)
        end = min(_month_end(start), today)
        prev_start = _month_start(today, offset=1)
        prev_end = _month_end(prev_start)
        return start, end, prev_start, prev_end, PERIOD_LABELS["this_month"], PERIOD_LABELS["last_month"]

    if period == "last_month":
        start = _month_start(today, offset=1)
        end = _month_end(start)
        prev_start = _month_start(today, offset=2)
        prev_end = _month_end(prev_start)
        return start, end, prev_start, prev_end, PERIOD_LABELS["last_month"], "الشهر قبل السابق"

    if period == "custom" and custom_start and custom_end:
        if custom_end < custom_start:
            custom_start, custom_end = custom_end, custom_start
        span = (custom_end - custom_start).days + 1
        prev_end = custom_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=span - 1)
        label = f"{custom_start.isoformat()} — {custom_end.isoformat()}"
        prev_label = f"{prev_start.isoformat()} — {prev_end.isoformat()}"
        return custom_start, custom_end, prev_start, prev_end, label, prev_label

    start = _week_start_sunday(today, offset=0)
    end = min(start + timedelta(days=6), today)
    prev_start = _week_start_sunday(today, offset=1)
    prev_end = prev_start + timedelta(days=6)
    return start, end, prev_start, prev_end, PERIOD_LABELS["this_week"], PERIOD_LABELS["last_week"]


async def _lessons_completed(db: AsyncSession, student_id: int, start_dt: datetime, end_dt: datetime) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(StudentLessonProgress)
        .where(
            StudentLessonProgress.student_id == student_id,
            StudentLessonProgress.completed_at.is_not(None),
            StudentLessonProgress.completed_at >= start_dt,
            StudentLessonProgress.completed_at < end_dt,
        )
    )
    return int(result.scalar_one() or 0)


async def _avg_quiz_score(db: AsyncSession, student_id: int, start_dt: datetime, end_dt: datetime) -> float | None:
    result = await db.execute(
        select(QuizAttempt)
        .where(
            QuizAttempt.student_id == student_id,
            QuizAttempt.created_at >= start_dt,
            QuizAttempt.created_at < end_dt,
        )
        .order_by(QuizAttempt.created_at.desc())
        .limit(50)
    )
    attempts = list(result.scalars().all())
    if not attempts:
        return None
    scores: list[int] = []
    for attempt in attempts:
        feedback = []
        if attempt.feedback_json:
            try:
                feedback = json.loads(attempt.feedback_json)
            except Exception:
                pass
        total = len(feedback) if feedback else max(attempt.correct_count, 1)
        scores.append(round((attempt.correct_count / total) * 100) if total else 0)
    return round(sum(scores) / len(scores), 1)


async def _planner_stats(db: AsyncSession, student_id: int, start_dt: datetime, end_dt: datetime) -> dict:
    now = _utcnow()
    result = await db.execute(
        select(PlannerScheduleSlot).where(
            PlannerScheduleSlot.student_id == student_id,
            PlannerScheduleSlot.scheduled_at >= start_dt,
            PlannerScheduleSlot.scheduled_at < end_dt,
        )
    )
    slots = list(result.scalars().all())
    completed = 0
    missed = 0
    overdue = 0
    due = 0
    for slot in slots:
        status = slot.status.value if hasattr(slot.status, "value") else str(slot.status)
        eff = status
        if status == ScheduleSlotStatus.planned.value and slot.scheduled_at < now:
            eff = "overdue"
        if eff == ScheduleSlotStatus.completed.value:
            completed += 1
            due += 1
        elif eff in (ScheduleSlotStatus.missed.value, "overdue"):
            if eff == ScheduleSlotStatus.missed.value:
                missed += 1
            else:
                overdue += 1
            due += 1
    adherence = int(round((completed / due) * 100)) if due else 0
    return {
        "adherence_percent": adherence,
        "completed": completed,
        "missed": missed,
        "overdue": overdue,
        "due": due,
    }


async def _weekly_lesson_buckets(
    db: AsyncSession, student_id: int, end: date, weeks: int = 8
) -> list[dict]:
    buckets: list[dict] = []
    for offset in range(weeks - 1, -1, -1):
        ws = _week_start_sunday(end, offset=offset)
        we = min(ws + timedelta(days=6), end)
        if ws > end:
            continue
        ws_dt, we_dt = _range_dt(ws, we)
        count = await _lessons_completed(db, student_id, ws_dt, we_dt)
        buckets.append(
            {
                "label": f"أسبوع {ws.strftime('%m/%d')}",
                "date": ws.isoformat(),
                "value": float(count),
            }
        )
    return buckets


async def _monthly_lesson_buckets(
    db: AsyncSession, student_id: int, end: date, months: int = 6
) -> list[dict]:
    buckets: list[dict] = []
    cursor = _month_start(end, offset=0)
    for offset in range(months - 1, -1, -1):
        ms = _month_start(end, offset=offset)
        me = _month_end(ms) if offset > 0 else min(_month_end(ms), end)
        ms_dt, me_dt = _range_dt(ms, me)
        count = await _lessons_completed(db, student_id, ms_dt, me_dt)
        buckets.append(
            {
                "label": ms.strftime("%Y-%m"),
                "date": ms.isoformat(),
                "value": float(count),
            }
        )
    return list(reversed(buckets))


async def _weekly_planner_trends(
    db: AsyncSession, student_id: int, end: date, weeks: int = 8
) -> tuple[list[dict], list[dict]]:
    adherence_trend: list[dict] = []
    missed_trend: list[dict] = []
    for offset in range(weeks - 1, -1, -1):
        ws = _week_start_sunday(end, offset=offset)
        we = ws + timedelta(days=6)
        if ws > end:
            continue
        ws_dt, we_dt = _range_dt(ws, we)
        stats = await _planner_stats(db, student_id, ws_dt, we_dt)
        label = f"أسبوع {ws.strftime('%m/%d')}"
        adherence_trend.append(
            {"label": label, "date": ws.isoformat(), "value": float(stats["adherence_percent"])}
        )
        missed_trend.append(
            {
                "label": label,
                "date": ws.isoformat(),
                "value": float(stats["missed"] + stats["overdue"]),
            }
        )
    return adherence_trend, missed_trend


async def build_parent_historical_report(
    db: AsyncSession,
    student_id: int,
    *,
    period: str = "this_week",
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    student = await db.get(User, student_id)
    if not student:
        return {"has_data": False}

    ctx = await build_linked_child_context(db, student)
    start, end, prev_start, prev_end, period_label, prev_label = resolve_period(
        period,
        custom_start=start_date,
        custom_end=end_date,
    )

    start_dt, end_dt = _range_dt(start, end)
    prev_start_dt, prev_end_dt = _range_dt(prev_start, prev_end)

    cur_seconds = await _sum_study_seconds(db, student_id, start_dt, end_dt)
    prev_seconds = await _sum_study_seconds(db, student_id, prev_start_dt, prev_end_dt)
    cur_hours = round(cur_seconds / 3600, 1)
    prev_hours = round(prev_seconds / 3600, 1)

    cur_lessons = await _lessons_completed(db, student_id, start_dt, end_dt)
    prev_lessons = await _lessons_completed(db, student_id, prev_start_dt, prev_end_dt)

    cur_grade = await _avg_quiz_score(db, student_id, start_dt, end_dt)
    prev_grade = await _avg_quiz_score(db, student_id, prev_start_dt, prev_end_dt)

    cur_planner = await _planner_stats(db, student_id, start_dt, end_dt)
    prev_planner = await _planner_stats(db, student_id, prev_start_dt, prev_end_dt)

    comparison = {
        "period_label": period_label,
        "previous_period_label": prev_label,
        "study_time": {
            "label": "وقت الدراسة",
            "current_value": cur_hours,
            "previous_value": prev_hours,
            "change_percent": _pct_change(cur_seconds, prev_seconds),
            "unit": "ساعة",
        },
        "grades": {
            "label": "متوسط الدرجات",
            "current_value": float(cur_grade or 0),
            "previous_value": float(prev_grade or 0),
            "change_percent": (
                _pct_change(int(cur_grade or 0), int(prev_grade or 0))
                if cur_grade is not None or prev_grade is not None
                else None
            ),
            "unit": "%",
        },
        "lesson_completion": {
            "label": "إكمال الدروس",
            "current_value": float(cur_lessons),
            "previous_value": float(prev_lessons),
            "change_percent": _pct_change(cur_lessons, prev_lessons),
            "unit": "درس",
        },
        "planner_adherence": {
            "label": "الالتزام بالخطة",
            "current_value": float(cur_planner["adherence_percent"]),
            "previous_value": float(prev_planner["adherence_percent"]),
            "change_percent": _pct_change(
                cur_planner["adherence_percent"], prev_planner["adherence_percent"]
            ),
            "unit": "%",
        },
    }

    by_day = await _daily_study_minutes(db, student_id, start, end)
    daily_trend = [
        {
            "label": _day_label(d),
            "date": d.isoformat(),
            "value": float(by_day.get(d, 0)),
        }
        for d in (start + timedelta(days=i) for i in range((end - start).days + 1))
    ]

    sessions = await _login_history(
        db, student_id, start_dt=start_dt, end_dt=end_dt, limit=100
    )

    weekly_lessons = await _weekly_lesson_buckets(db, student_id, end)
    monthly_lessons = await _monthly_lesson_buckets(db, student_id, end)
    adherence_trend, missed_trend = await _weekly_planner_trends(db, student_id, end)

    avg_adherence = (
        round(sum(p["value"] for p in adherence_trend) / len(adherence_trend), 1)
        if adherence_trend
        else 0
    )
    total_missed = int(sum(p["value"] for p in missed_trend))

    has_data = bool(
        cur_seconds or cur_lessons or cur_grade is not None or cur_planner["due"] or sessions
    )

    report = {
        "student_name": ctx["name"],
        "grade_label": ctx.get("grade_label") or grade_label(ctx.get("grade")),
        "period": period,
        "period_label": period_label,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "comparison": comparison,
        "lesson_history": {
            "weekly": weekly_lessons,
            "monthly": monthly_lessons,
            "total_in_period": cur_lessons,
        },
        "attendance_history": {
            "login_sessions": sessions,
            "daily_study_trend": daily_trend,
            "total_study_hours": cur_hours,
            "total_sessions": len(sessions),
        },
        "planner_history": {
            "adherence_trend": adherence_trend,
            "missed_tasks_trend": missed_trend,
            "average_adherence": avg_adherence,
            "total_missed": total_missed,
        },
        "has_data": has_data,
    }

    from app.services.parent_report_pdf_analytics import build_pdf_analytics

    report["pdf_analytics"] = await build_pdf_analytics(db, student_id, report)
    return report
