"""Shared student context fields for parent portal (grade, activity status)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import StudentProfile
from app.models.user import User

ACTIVE_NOW_MINUTES = 15
ACTIVE_TODAY_MINUTES = 24 * 60


def grade_label(grade: int | None) -> str:
    if grade is None:
        return ""
    return f"الصف {grade}"


def resolve_academic_status(last_activity_at: datetime | None) -> tuple[str, str]:
    if not last_activity_at:
        return "inactive", "غير نشط"
    now = datetime.now(timezone.utc)
    if last_activity_at.tzinfo is None:
        last_activity_at = last_activity_at.replace(tzinfo=timezone.utc)
    minutes_ago = (now - last_activity_at).total_seconds() / 60
    if minutes_ago <= ACTIVE_NOW_MINUTES:
        return "active_now", "نشط الآن"
    if minutes_ago <= ACTIVE_TODAY_MINUTES:
        return "active_today", "نشط اليوم"
    return "inactive", "غير متصل مؤخراً"


async def build_linked_child_context(db: AsyncSession, student: User) -> dict:
    profile = (
        await db.execute(select(StudentProfile).where(StudentProfile.user_id == student.id))
    ).scalar_one_or_none()
    last_at = profile.last_activity_at if profile else None
    status, status_label = resolve_academic_status(last_at)
    grade = profile.grade if profile else None
    return {
        "id": student.id,
        "name": student.name,
        "email": student.email,
        "grade": grade,
        "grade_label": grade_label(grade),
        "academic_status": status,
        "academic_status_label": status_label,
        "last_activity_at": last_at.isoformat() if last_at else None,
    }
