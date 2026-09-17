"""Record daily attendance from real student activity (lessons, quizzes, planner)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceStatus, StudentAttendanceRecord
from app.services.attendance_service import _status_score


async def _get_or_create_today(
    db: AsyncSession, student_id: int, *, today: date | None = None
) -> StudentAttendanceRecord:
    today = today or datetime.now(timezone.utc).date()
    result = await db.execute(
        select(StudentAttendanceRecord).where(
            StudentAttendanceRecord.student_id == student_id,
            StudentAttendanceRecord.date == today,
        )
    )
    rec = result.scalar_one_or_none()
    if rec:
        return rec
    rec = StudentAttendanceRecord(
        student_id=student_id,
        date=today,
        status=AttendanceStatus.absent,
        study_minutes=0,
        consistency_score=0,
    )
    db.add(rec)
    await db.flush()
    return rec


async def record_study_minutes(
    db: AsyncSession,
    student_id: int,
    minutes: int,
    *,
    source: str | None = None,
) -> StudentAttendanceRecord:
    """Upsert today's attendance from study activity."""
    if minutes <= 0:
        return await _get_or_create_today(db, student_id)
    return await _apply_study_seconds(db, student_id, minutes * 60, source=source)


async def record_study_seconds(
    db: AsyncSession,
    student_id: int,
    seconds: int,
    *,
    source: str | None = None,
) -> StudentAttendanceRecord:
    """Upsert today's attendance from tracked active seconds (real platform activity)."""
    if seconds <= 0:
        return await _get_or_create_today(db, student_id)
    return await _apply_study_seconds(db, student_id, seconds, source=source)


async def _apply_study_seconds(
    db: AsyncSession,
    student_id: int,
    seconds: int,
    *,
    source: str | None = None,
) -> StudentAttendanceRecord:
    rec = await _get_or_create_today(db, student_id)
    added_minutes = max(1, seconds // 60) if seconds >= 30 else 0
    if added_minutes <= 0:
        return rec
    rec.study_minutes = int(rec.study_minutes or 0) + added_minutes

    if rec.study_minutes >= 60:
        rec.status = AttendanceStatus.present
    elif rec.study_minutes >= 20:
        rec.status = AttendanceStatus.partial
    else:
        rec.status = AttendanceStatus.partial

    rec.consistency_score = _status_score(rec.status, rec.study_minutes)
    if source:
        rec.notes = (rec.notes or "") + (f" · {source}" if rec.notes else source)
    await db.flush()
    return rec


async def on_lesson_completed(db: AsyncSession, student_id: int, lesson_id: int) -> None:
    """Deprecated fixed-minute hook — study time comes from activity tracking."""
    return None


async def on_quiz_submitted(db: AsyncSession, student_id: int, quiz_id: int) -> None:
    """Deprecated fixed-minute hook — study time comes from activity tracking."""
    return None


async def on_study_session_completed(
    db: AsyncSession, student_id: int, minutes: int, *, slot_id: int | None = None
) -> None:
    """Deprecated fixed-minute hook — study time comes from activity tracking."""
    return None
