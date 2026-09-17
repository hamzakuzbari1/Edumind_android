"""Parent ↔ student linking via invite codes."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parent_link import DEFAULT_RELATIONSHIP_LABEL, ParentStudentLink
from app.models.profile import StudentProfile
from app.models.user import User, UserRole


def _generate_code() -> str:
    return secrets.token_hex(4).upper()


async def ensure_student_link_code(db: AsyncSession, student_user_id: int) -> str:
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == student_user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="ملف الطالب غير موجود")
    if profile.parent_link_code:
        return profile.parent_link_code
    code = _generate_code()
    profile.parent_link_code = code
    await db.flush()
    return code


async def link_parent_to_student_by_id(
    db: AsyncSession, parent_id: int, student_id: int
) -> ParentStudentLink:
    if parent_id == student_id:
        raise HTTPException(status_code=400, detail="لا يمكن ربط الحساب بنفسه")

    student = await db.get(User, student_id)
    if not student or student.role != UserRole.student:
        raise HTTPException(status_code=404, detail="حساب الطالب غير موجود")

    existing = await db.execute(
        select(ParentStudentLink).where(
            ParentStudentLink.parent_id == parent_id,
            ParentStudentLink.student_id == student_id,
        )
    )
    link = existing.scalar_one_or_none()
    if link:
        return link

    link = ParentStudentLink(
        parent_id=parent_id,
        student_id=student_id,
        relationship_label=DEFAULT_RELATIONSHIP_LABEL,
    )
    db.add(link)
    await db.flush()
    return link


async def link_parent_to_student(db: AsyncSession, parent_id: int, link_code: str) -> ParentStudentLink:
    code = link_code.strip().upper()
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.parent_link_code == code)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="رمز الربط غير صالح")

    if profile.user_id == parent_id:
        raise HTTPException(status_code=400, detail="لا يمكن ربط الحساب بنفسه")

    existing = await db.execute(
        select(ParentStudentLink).where(
            ParentStudentLink.parent_id == parent_id,
            ParentStudentLink.student_id == profile.user_id,
        )
    )
    link = existing.scalar_one_or_none()
    if link:
        return link

    return await link_parent_to_student_by_id(db, parent_id, profile.user_id)


async def list_linked_students(db: AsyncSession, parent_id: int) -> list[User]:
    result = await db.execute(
        select(User)
        .join(ParentStudentLink, ParentStudentLink.student_id == User.id)
        .where(ParentStudentLink.parent_id == parent_id)
        .order_by(User.name)
    )
    return list(result.scalars().all())


async def unlink_student(db: AsyncSession, parent_id: int, student_id: int) -> None:
    result = await db.execute(
        select(ParentStudentLink).where(
            ParentStudentLink.parent_id == parent_id,
            ParentStudentLink.student_id == student_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="الربط غير موجود")
    await db.delete(link)
    await db.flush()


async def resolve_parent_student_id(
    db: AsyncSession, parent: User, student_id: int | None = None
) -> int:
    if parent.role != UserRole.parent:
        return parent.id

    links = await list_linked_students(db, parent.id)
    if not links:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لم يتم ربط أي طالب — أضف طالباً من لوحة المتابعة",
        )

    if student_id is None:
        return links[0].id

    if not any(s.id == student_id for s in links):
        raise HTTPException(status_code=403, detail="هذا الطالب غير مرتبط بحسابك")
    return student_id


async def record_parent_view(db: AsyncSession, parent_id: int, student_id: int) -> None:
    result = await db.execute(
        select(ParentStudentLink).where(
            ParentStudentLink.parent_id == parent_id,
            ParentStudentLink.student_id == student_id,
        )
    )
    link = result.scalar_one_or_none()
    if link:
        link.last_viewed_at = datetime.now(timezone.utc)
        await db.flush()
