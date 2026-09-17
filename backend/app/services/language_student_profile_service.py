"""Canonical LanguageStudentProfile lookup by (student_id, language_id)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.profile import LanguageStudentProfile


async def get_language_student_profile(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LanguageStudentProfile | None:
    return (
        await db.execute(
            select(LanguageStudentProfile).where(
                LanguageStudentProfile.student_id == student_id,
                LanguageStudentProfile.language_id == language_id,
            )
        )
    ).scalar_one_or_none()


async def get_or_create_language_student_profile(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LanguageStudentProfile:
    profile = await get_language_student_profile(
        db, student_id=student_id, language_id=language_id
    )
    if profile is None:
        profile = LanguageStudentProfile(student_id=student_id, language_id=language_id)
        db.add(profile)
        await db.flush()
    return profile
