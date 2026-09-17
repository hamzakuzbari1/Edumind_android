"""Deterministic study schedule optimization engine."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planner import (
    LifeEventType,
    PlannerLifeEvent,
    PlannerProfile,
    PlannerScheduleSlot,
    ScheduleSlotStatus,
)

DEFAULT_SUBJECTS = ["رياضيات", "كيمياء", "فيزياء", "عربي", "إنجليزي"]

PERIOD_HOURS = {
    "morning": (9, 12),
    "evening": (16, 20),
    "night": (20, 23),
}


def _parse_time(t: str) -> tuple[int, int]:
    parts = t.split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


def _time_in_range(hour: int, start: str, end: str) -> bool:
    sh, _ = _parse_time(start)
    eh, _ = _parse_time(end)
    return sh <= hour < eh


def _slot_datetime(day: datetime, hour: int, minute: int = 0) -> datetime:
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0, tzinfo=timezone.utc)


def _is_blocked(slot_dt: datetime, duration: int, events: list[PlannerLifeEvent], profile: PlannerProfile) -> bool:
    hour = slot_dt.hour
    if _time_in_range(hour, profile.school_start, profile.school_end):
        if slot_dt.weekday() < 5:
            return True
    end_dt = slot_dt + timedelta(minutes=duration)
    for ev in events:
        if ev.is_blocking and ev.day_of_week is not None and slot_dt.weekday() != ev.day_of_week:
            continue
        if ev.event_date and ev.event_date.date() != slot_dt.date():
            continue
        if ev.start_time:
            eh, em = _parse_time(ev.start_time)
            ev_start = slot_dt.replace(hour=eh, minute=em)
            ev_end = ev_start + timedelta(minutes=ev.duration_minutes)
            if slot_dt < ev_end and end_dt > ev_start:
                return True
    return False


def _subject_priority(subject: str, weak: list[str], exams: list[PlannerLifeEvent]) -> int:
    priority = 1
    if subject in weak:
        priority += 3
    for ex in exams:
        if ex.subject == subject:
            priority += 5
    return priority


async def optimize_schedule(
    db: AsyncSession,
    student_id: int,
    profile: PlannerProfile,
    *,
    days: int = 7,
) -> tuple[list[PlannerScheduleSlot], list[str]]:
    weak = []
    import json

    try:
        weak = json.loads(profile.weak_subjects_json or "[]")
    except Exception:
        weak = []

    ev_result = await db.execute(
        select(PlannerLifeEvent).where(PlannerLifeEvent.student_id == student_id)
    )
    life_events = list(ev_result.scalars().all())
    exams = [e for e in life_events if e.event_type == LifeEventType.exam]

    await db.execute(
        delete(PlannerScheduleSlot).where(
            PlannerScheduleSlot.student_id == student_id,
            PlannerScheduleSlot.status == ScheduleSlotStatus.planned,
        )
    )

    period = profile.preferred_period or "evening"
    start_h, end_h = PERIOD_HOURS.get(period, PERIOD_HOURS["evening"])
    subjects = list(dict.fromkeys(weak + DEFAULT_SUBJECTS))
    reasoning: list[str] = []
    slots: list[PlannerScheduleSlot] = []

    if weak:
        reasoning.append(f"أولوية للمواد الضعيفة: {', '.join(weak)}")
    if exams:
        exam_subjects = [e.subject for e in exams if e.subject]
        if exam_subjects:
            reasoning.append(f"تكثيف المراجعة قبل الامتحان: {', '.join(exam_subjects)}")
    reasoning.append(f"فترة الدراسة المفضلة: {_period_label(period)}")
    reasoning.append(f"حد أقصى يومي: {profile.max_daily_minutes} دقيقة مع فترات راحة")

    now = datetime.now(timezone.utc)
    session_minutes = 45
    break_minutes = 15
    subject_idx = 0

    for day_offset in range(days):
        day = (now + timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        daily_minutes = 0
        hour = start_h

        while hour < end_h and daily_minutes + session_minutes <= profile.max_daily_minutes:
            subject = subjects[subject_idx % len(subjects)]
            slot_dt = _slot_datetime(day, hour)
            if slot_dt <= now:
                hour += 1
                continue
            if _is_blocked(slot_dt, session_minutes, life_events, profile):
                hour += 1
                continue

            priority = _subject_priority(subject, weak, exams)
            reason_parts = []
            if subject in weak:
                reason_parts.append("مادة ضعيفة")
            if any(e.subject == subject for e in exams):
                reason_parts.append("قرب الامتحان")

            slot = PlannerScheduleSlot(
                student_id=student_id,
                subject=subject,
                scheduled_at=slot_dt,
                duration_minutes=session_minutes,
                priority=priority,
                status=ScheduleSlotStatus.planned,
                reasoning=" — ".join(reason_parts) if reason_parts else "مراجعة منتظمة",
            )
            db.add(slot)
            slots.append(slot)
            daily_minutes += session_minutes + break_minutes
            subject_idx += 1
            hour += 1
            if session_minutes >= 45 and daily_minutes % 90 == 0:
                reasoning.append(f"استراحة بعد جلسة {subject} يوم {day.strftime('%d/%m')}")

    await db.flush()
    return slots, reasoning


def _period_label(period: str) -> str:
    return {"morning": "الصباح", "evening": "المساء", "night": "الليل"}.get(period, period)
