"""CRUD for teacher profile CV sections."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import TeacherProfile
from app.models.teacher_profile_cv import (
    TeacherAchievement,
    TeacherQualification,
    TeacherTeachingExperience,
)
from app.models.user import User
from app.schemas.teacher_profile_cv import (
    TeacherAchievementCreate,
    TeacherAchievementOut,
    TeacherAchievementUpdate,
    TeacherProfileCvOut,
    TeacherQualificationCreate,
    TeacherQualificationOut,
    TeacherQualificationUpdate,
    TeacherTeachingExperienceCreate,
    TeacherTeachingExperienceOut,
    TeacherTeachingExperienceUpdate,
)
from app.services.teacher_setup_service import get_or_create_teacher_profile


def _qualification_out(row: TeacherQualification) -> TeacherQualificationOut:
    return TeacherQualificationOut(
        id=row.id,
        title=row.title,
        institution=row.institution,
        year=row.year,
        description=row.description,
        sort_order=row.sort_order,
    )


def _experience_out(row: TeacherTeachingExperience) -> TeacherTeachingExperienceOut:
    return TeacherTeachingExperienceOut(
        id=row.id,
        title=row.title,
        organization=row.organization,
        year_from=row.year_from,
        year_to=row.year_to,
        description=row.description,
        sort_order=row.sort_order,
    )


def _achievement_out(row: TeacherAchievement) -> TeacherAchievementOut:
    return TeacherAchievementOut(
        id=row.id,
        title=row.title,
        year=row.year,
        description=row.description,
        sort_order=row.sort_order,
        is_pinned=bool(row.is_pinned),
    )


async def load_teacher_profile_cv(db: AsyncSession, teacher_profile_id: int) -> TeacherProfileCvOut:
    result = await db.execute(
        select(TeacherProfile)
        .where(TeacherProfile.id == teacher_profile_id)
        .options(
            selectinload(TeacherProfile.qualifications),
            selectinload(TeacherProfile.teaching_experiences),
            selectinload(TeacherProfile.achievements),
        )
    )
    tp = result.scalar_one_or_none()
    if not tp:
        return TeacherProfileCvOut()
    return TeacherProfileCvOut(
        qualifications=[_qualification_out(q) for q in tp.qualifications],
        teaching_experiences=[_experience_out(e) for e in tp.teaching_experiences],
        achievements=sorted(
            [_achievement_out(a) for a in tp.achievements],
            key=lambda a: (not a.is_pinned, a.sort_order, a.id),
        ),
    )


async def get_teacher_cv(db: AsyncSession, user: User) -> TeacherProfileCvOut:
    tp = await get_or_create_teacher_profile(db, user)
    return await load_teacher_profile_cv(db, tp.id)


async def _get_owned_qualification(
    db: AsyncSession, user: User, entry_id: int
) -> tuple[TeacherProfile, TeacherQualification]:
    tp = await get_or_create_teacher_profile(db, user)
    row = await db.get(TeacherQualification, entry_id)
    if not row or row.teacher_profile_id != tp.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المؤهل غير موجود")
    return tp, row


async def create_qualification(
    db: AsyncSession, user: User, body: TeacherQualificationCreate
) -> TeacherQualificationOut:
    tp = await get_or_create_teacher_profile(db, user)
    row = TeacherQualification(
        teacher_profile_id=tp.id,
        title=body.title.strip(),
        institution=body.institution.strip() if body.institution else None,
        year=body.year,
        description=body.description.strip() if body.description else None,
        sort_order=body.sort_order,
    )
    db.add(row)
    await db.flush()
    return _qualification_out(row)


async def update_qualification(
    db: AsyncSession, user: User, entry_id: int, body: TeacherQualificationUpdate
) -> TeacherQualificationOut:
    _, row = await _get_owned_qualification(db, user, entry_id)
    if body.title is not None:
        row.title = body.title.strip()
    if body.institution is not None:
        row.institution = body.institution.strip() or None
    if body.year is not None:
        row.year = body.year
    if body.description is not None:
        row.description = body.description.strip() or None
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    await db.flush()
    return _qualification_out(row)


async def delete_qualification(db: AsyncSession, user: User, entry_id: int) -> None:
    _, row = await _get_owned_qualification(db, user, entry_id)
    await db.delete(row)
    await db.flush()


async def _get_owned_experience(
    db: AsyncSession, user: User, entry_id: int
) -> tuple[TeacherProfile, TeacherTeachingExperience]:
    tp = await get_or_create_teacher_profile(db, user)
    row = await db.get(TeacherTeachingExperience, entry_id)
    if not row or row.teacher_profile_id != tp.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الخبرة غير موجودة")
    return tp, row


async def create_teaching_experience(
    db: AsyncSession, user: User, body: TeacherTeachingExperienceCreate
) -> TeacherTeachingExperienceOut:
    tp = await get_or_create_teacher_profile(db, user)
    row = TeacherTeachingExperience(
        teacher_profile_id=tp.id,
        title=body.title.strip(),
        organization=body.organization.strip() if body.organization else None,
        year_from=body.year_from,
        year_to=body.year_to,
        description=body.description.strip() if body.description else None,
        sort_order=body.sort_order,
    )
    db.add(row)
    await db.flush()
    return _experience_out(row)


async def update_teaching_experience(
    db: AsyncSession, user: User, entry_id: int, body: TeacherTeachingExperienceUpdate
) -> TeacherTeachingExperienceOut:
    _, row = await _get_owned_experience(db, user, entry_id)
    if body.title is not None:
        row.title = body.title.strip()
    if body.organization is not None:
        row.organization = body.organization.strip() or None
    if body.year_from is not None:
        row.year_from = body.year_from
    if body.year_to is not None:
        row.year_to = body.year_to
    if body.description is not None:
        row.description = body.description.strip() or None
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    await db.flush()
    return _experience_out(row)


async def delete_teaching_experience(db: AsyncSession, user: User, entry_id: int) -> None:
    _, row = await _get_owned_experience(db, user, entry_id)
    await db.delete(row)
    await db.flush()


async def _get_owned_achievement(
    db: AsyncSession, user: User, entry_id: int
) -> tuple[TeacherProfile, TeacherAchievement]:
    tp = await get_or_create_teacher_profile(db, user)
    row = await db.get(TeacherAchievement, entry_id)
    if not row or row.teacher_profile_id != tp.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الإنجاز غير موجود")
    return tp, row


async def create_achievement(
    db: AsyncSession, user: User, body: TeacherAchievementCreate
) -> TeacherAchievementOut:
    tp = await get_or_create_teacher_profile(db, user)
    row = TeacherAchievement(
        teacher_profile_id=tp.id,
        title=body.title.strip(),
        year=body.year,
        description=body.description.strip() if body.description else None,
        sort_order=body.sort_order,
        is_pinned=body.is_pinned,
    )
    db.add(row)
    await db.flush()
    return _achievement_out(row)


async def update_achievement(
    db: AsyncSession, user: User, entry_id: int, body: TeacherAchievementUpdate
) -> TeacherAchievementOut:
    _, row = await _get_owned_achievement(db, user, entry_id)
    if body.title is not None:
        row.title = body.title.strip()
    if body.year is not None:
        row.year = body.year
    if body.description is not None:
        row.description = body.description.strip() or None
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    if body.is_pinned is not None:
        row.is_pinned = body.is_pinned
    await db.flush()
    return _achievement_out(row)


async def delete_achievement(db: AsyncSession, user: User, entry_id: int) -> None:
    _, row = await _get_owned_achievement(db, user, entry_id)
    await db.delete(row)
    await db.flush()
