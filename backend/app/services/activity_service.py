"""Student activity event tracking for parent monitoring."""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityEventType, StudentActivityEvent

logger = logging.getLogger(__name__)

AR_DAYS = {
    0: "الاثنين",
    1: "الثلاثاء",
    2: "الأربعاء",
    3: "الخميس",
    4: "الجمعة",
    5: "السبت",
    6: "الأحد",
}


def relative_time_ar(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "الآن"
    if seconds < 3600:
        mins = seconds // 60
        return f"منذ {mins} دقيقة" if mins > 1 else "منذ دقيقة"
    if seconds < 86400:
        hours = seconds // 3600
        return f"منذ {hours} ساعة" if hours > 1 else "منذ ساعة"
    days = seconds // 86400
    if days == 1:
        return "منذ يوم"
    if days < 7:
        return f"منذ {days} أيام"
    return dt.strftime("%d/%m/%Y")


async def log_activity(
    db: AsyncSession,
    *,
    student_id: int,
    event_type: ActivityEventType,
    title: str,
    description: str | None = None,
    payload: dict | None = None,
) -> StudentActivityEvent:
    event = StudentActivityEvent(
        student_id=student_id,
        event_type=event_type,
        title=title,
        description=description,
        payload_json=json.dumps(payload or {}, ensure_ascii=False),
    )
    db.add(event)
    await db.flush()
    return event


async def log_quiz_submitted(
    db: AsyncSession,
    *,
    student_id: int,
    student_name: str,
    subject: str,
    score_percent: int,
    lesson_id: int,
) -> StudentActivityEvent:
    title = f"ابنك {student_name} أجرى اختبار {subject} وحصل على {score_percent}%"
    return await log_activity(
        db,
        student_id=student_id,
        event_type=ActivityEventType.quiz_submitted,
        title=title,
        description=f"نتيجة الاختبار: {score_percent}%",
        payload={"subject": subject, "score_percent": score_percent, "lesson_id": lesson_id},
    )


async def log_lesson_completed(
    db: AsyncSession,
    *,
    student_id: int,
    student_name: str,
    lesson_title: str,
    subject: str,
    lesson_id: int,
) -> StudentActivityEvent:
    title = f"ابنك {student_name} أكمل درس {subject}: {lesson_title}"
    return await log_activity(
        db,
        student_id=student_id,
        event_type=ActivityEventType.lesson_activity,
        title=title,
        description="اكتمل الدرس بعد استيفاء متطلبات التعلم",
        payload={"subject": subject, "lesson_id": lesson_id, "lesson_title": lesson_title},
    )


async def log_study_session_completed(
    db: AsyncSession,
    *,
    student_id: int,
    student_name: str,
    subject: str,
    slot_id: int | None = None,
    duration_minutes: int = 30,
) -> StudentActivityEvent:
    from app.services.attendance_activity_service import on_study_session_completed

    await on_study_session_completed(db, student_id, duration_minutes, slot_id=slot_id)
    title = f"{student_name} أكمل جلسة دراسة {subject}"
    return await log_activity(
        db,
        student_id=student_id,
        event_type=ActivityEventType.study_session_completed,
        title=title,
        payload={"subject": subject, "slot_id": slot_id},
    )


async def log_planner_generated(
    db: AsyncSession,
    *,
    student_id: int,
    student_name: str,
    slot_count: int,
) -> StudentActivityEvent:
    title = "تم إنشاء خطة دراسة جديدة"
    desc = f"خطة مُحسّنة لـ {student_name} — {slot_count} جلسات"
    return await log_activity(
        db,
        student_id=student_id,
        event_type=ActivityEventType.planner_generated,
        title=title,
        description=desc,
        payload={"slot_count": slot_count},
    )


async def log_weak_subject_alert(
    db: AsyncSession,
    *,
    student_id: int,
    student_name: str,
    subject: str,
) -> StudentActivityEvent:
    title = f"تنبيه: {student_name} يحتاج دعماً في {subject}"
    return await log_activity(
        db,
        student_id=student_id,
        event_type=ActivityEventType.weak_subject_alert,
        title=title,
        payload={"subject": subject},
    )


async def log_performance_improved(
    db: AsyncSession,
    *,
    student_id: int,
    student_name: str,
    subject: str,
    improvement_percent: int,
) -> StudentActivityEvent:
    title = f"تحسن أداء {student_name} في {subject} بنسبة {improvement_percent}%"
    return await log_activity(
        db,
        student_id=student_id,
        event_type=ActivityEventType.performance_improved,
        title=title,
        payload={"subject": subject, "improvement_percent": improvement_percent},
    )


async def log_weekly_summary(
    db: AsyncSession,
    *,
    student_id: int,
    student_name: str,
    session_count: int,
) -> StudentActivityEvent:
    title = f"{student_name} أنهى {session_count} جلسات دراسة هذا الأسبوع"
    return await log_activity(
        db,
        student_id=student_id,
        event_type=ActivityEventType.weekly_summary,
        title=title,
        payload={"session_count": session_count},
    )


async def check_and_log_no_study_today(db: AsyncSession, student_id: int, student_name: str) -> None:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count())
        .select_from(StudentActivityEvent)
        .where(
            StudentActivityEvent.student_id == student_id,
            StudentActivityEvent.event_type == ActivityEventType.study_session_completed,
            StudentActivityEvent.created_at >= today_start,
        )
    )
    if result.scalar_one() == 0:
        existing = await db.execute(
            select(func.count())
            .select_from(StudentActivityEvent)
            .where(
                StudentActivityEvent.student_id == student_id,
                StudentActivityEvent.event_type == ActivityEventType.no_study_today,
                StudentActivityEvent.created_at >= today_start,
            )
        )
        if existing.scalar_one() == 0:
            await log_activity(
                db,
                student_id=student_id,
                event_type=ActivityEventType.no_study_today,
                title=f"{student_name} لم يدرس اليوم",
            )


async def list_activities(
    db: AsyncSession,
    student_id: int,
    *,
    limit: int = 30,
) -> list[dict]:
    result = await db.execute(
        select(StudentActivityEvent)
        .where(StudentActivityEvent.student_id == student_id)
        .order_by(StudentActivityEvent.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()
    out = []
    for ev in events:
        payload = {}
        if ev.payload_json:
            try:
                payload = json.loads(ev.payload_json)
            except Exception:
                payload = {}
        out.append(
            {
                "id": ev.id,
                "event_type": ev.event_type.value,
                "title": ev.title,
                "description": ev.description,
                "payload": payload,
                "created_at": ev.created_at,
                "relative_time": relative_time_ar(ev.created_at),
            }
        )
    return out


async def count_weekly_sessions(db: AsyncSession, student_id: int) -> int:
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(func.count())
        .select_from(StudentActivityEvent)
        .where(
            StudentActivityEvent.student_id == student_id,
            StudentActivityEvent.event_type == ActivityEventType.study_session_completed,
            StudentActivityEvent.created_at >= week_ago,
        )
    )
    return result.scalar_one()


async def maybe_log_weekly_summary(db: AsyncSession, student_id: int, student_name: str) -> None:
    count = await count_weekly_sessions(db, student_id)
    if count >= 4:
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        existing = await db.execute(
            select(func.count())
            .select_from(StudentActivityEvent)
            .where(
                StudentActivityEvent.student_id == student_id,
                StudentActivityEvent.event_type == ActivityEventType.weekly_summary,
                StudentActivityEvent.created_at >= week_ago,
            )
        )
        if existing.scalar_one() == 0:
            await log_weekly_summary(db, student_id=student_id, student_name=student_name, session_count=count)
