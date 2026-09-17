"""Teacher first-time setup."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.academic_grades import is_valid_academic_grade, validate_academic_grade, MIN_ACADEMIC_GRADE, MAX_ACADEMIC_GRADE
from app.core.config import get_settings
from app.core.reference_catalog import is_subject_allowed_for_grade
from app.models.catalog import Course, Subject, TeacherProfile, TeacherProfileGrade, TeacherProfileSubject
from app.models.user import User
from app.schemas.teacher_setup import TeacherSetupStatusOut
from app.utils.media_urls import public_upload_url, teacher_avatar_url

settings = get_settings()


async def get_or_create_teacher_profile(db: AsyncSession, user: User) -> TeacherProfile:
    result = await db.execute(select(TeacherProfile).where(TeacherProfile.user_id == user.id))
    tp = result.scalar_one_or_none()
    if tp:
        return tp
    tp = TeacherProfile(user_id=user.id, full_name=user.name, bio=None, rating=4.8, student_count=0)
    db.add(tp)
    await db.flush()
    return tp


async def get_setup_status(db: AsyncSession, user: User) -> TeacherSetupStatusOut:
    tp = await get_or_create_teacher_profile(db, user)
    subj_ids = [
        r[0]
        for r in (
            await db.execute(
                select(TeacherProfileSubject.subject_id).where(
                    TeacherProfileSubject.teacher_profile_id == tp.id
                )
            )
        ).all()
    ]
    grades = [
        r[0]
        for r in (
            await db.execute(
                select(TeacherProfileGrade.grade).where(TeacherProfileGrade.teacher_profile_id == tp.id)
            )
        ).all()
    ]
    avatar = teacher_avatar_url(tp.image_url)
    display = (tp.full_name or user.name or "").strip() or None
    return TeacherSetupStatusOut(
        setup_complete=bool(tp.setup_completed_at),
        full_name=tp.full_name,
        display_name=display,
        image_url=avatar,
        avatar_url=avatar,
        bio=tp.bio,
        subject_ids=subj_ids,
        grades=grades,
    )


async def update_profile(db: AsyncSession, user: User, full_name: str, bio: str | None) -> TeacherSetupStatusOut:
    from app.services.audit_service import log_audit

    tp = await get_or_create_teacher_profile(db, user)
    old = {"full_name": tp.full_name, "bio": tp.bio}
    tp.full_name = full_name.strip()
    tp.bio = bio
    user.name = full_name.strip()
    await db.flush()
    await log_audit(
        db,
        action="update",
        entity_type="teacher_profile",
        entity_id=tp.id,
        actor_user_id=user.id,
        old_values=old,
        new_values={"full_name": tp.full_name, "bio": tp.bio},
    )
    return await get_setup_status(db, user)


def save_profile_image(user_id: int, filename: str, content: bytes) -> str:
    """Legacy local-only helper (kept for callers); prefer save_profile_image_async."""
    upload_root = Path(settings.UPLOAD_DIR) / "teachers" / str(user_id)
    upload_root.mkdir(parents=True, exist_ok=True)
    dest = upload_root / filename
    dest.write_bytes(content)
    rel = dest.resolve().relative_to(Path(settings.UPLOAD_DIR).resolve())
    return "/uploads/" + "/".join(rel.parts)


async def save_profile_image_async(
    db: AsyncSession,
    user: User,
    *,
    filename: str,
    content: bytes,
    mime_type: str | None = None,
) -> str:
    """Upload teacher avatar via storage provider; public-safe on edumind-public when supabase."""
    from app.models.media import MediaAccessScope
    from app.services.media_storage.upload import build_object_key, store_and_register_media

    object_key = build_object_key(
        "avatars",
        f"teacher_{user.id}",
        filename=filename or "avatar.jpg",
    )
    stored = await store_and_register_media(
        db,
        content=content,
        filename=filename or "avatar.jpg",
        mime_type=mime_type,
        uploaded_by_user_id=user.id,
        access_scope=MediaAccessScope.public.value,
        object_key=object_key,
        kind="avatar",
        max_bytes=5 * 1024 * 1024,
        metadata_json={"kind": "teacher_avatar", "user_id": user.id},
        keep_local_working_copy=False,
    )
    user.avatar_media_object_id = stored.media.id
    await db.flush()
    return stored.client_url


async def set_profile_image(db: AsyncSession, user: User, image_url: str) -> TeacherSetupStatusOut:
    tp = await get_or_create_teacher_profile(db, user)
    tp.image_url = image_url
    await db.flush()
    await db.refresh(tp)
    return await get_setup_status(db, user)


async def update_teaching(
    db: AsyncSession, user: User, subject_ids: list[int], grades: list[int]
) -> TeacherSetupStatusOut:
    tp = await get_or_create_teacher_profile(db, user)

    if not grades:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اختر صفاً واحداً على الأقل")
    if not subject_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اختر مادة واحدة على الأقل")

    grade_set: set[int] = set()
    for g in grades:
        if not is_valid_academic_grade(g):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"الصف يجب أن يكون بين {MIN_ACADEMIC_GRADE} و {MAX_ACADEMIC_GRADE}",
            )
        grade_set.add(g)

    unique_subject_ids = list(dict.fromkeys(subject_ids))
    result = await db.execute(
        select(Subject).where(
            Subject.id.in_(unique_subject_ids),
            Subject.is_active.is_(True),
        )
    )
    subjects = result.scalars().all()
    if len(subjects) != len(unique_subject_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="مادة غير صالحة أو غير متاحة")

    for subj in subjects:
        if subj.grade not in grade_set:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"المادة {subj.name_ar} (الصف {subj.grade}) لا تتوافق مع الصفوف المختارة",
            )
        if not is_subject_allowed_for_grade(subj.slug, subj.grade):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"المادة {subj.name_ar} غير متاحة للصف {subj.grade}",
            )

    await db.execute(delete(TeacherProfileSubject).where(TeacherProfileSubject.teacher_profile_id == tp.id))
    await db.execute(delete(TeacherProfileGrade).where(TeacherProfileGrade.teacher_profile_id == tp.id))
    for sid in unique_subject_ids:
        db.add(TeacherProfileSubject(teacher_profile_id=tp.id, subject_id=sid))
    for g in sorted(grade_set):
        db.add(TeacherProfileGrade(teacher_profile_id=tp.id, grade=g))

    await db.flush()
    return await get_setup_status(db, user)


async def create_course(
    db: AsyncSession,
    user: User,
    *,
    title: str,
    subject_id: int,
    grade: int,
    price: float,
) -> TeacherSetupStatusOut:
    validate_academic_grade(grade)
    tp = await get_or_create_teacher_profile(db, user)
    from app.models.catalog import Subject

    subj = await db.get(Subject, subject_id)
    if not subj or subj.grade != grade:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المادة غير متوافقة مع الصف")

    existing = await db.execute(
        select(Course).where(
            Course.teacher_profile_id == tp.id,
            Course.subject_id == subject_id,
            Course.grade == grade,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الدورة موجودة مسبقاً لهذه المادة")

    db.add(
        Course(
            title=title,
            subject_id=subject_id,
            teacher_profile_id=tp.id,
            grade=grade,
            price=price,
            currency="SYP",
            is_active=True,
        )
    )
    await db.flush()
    return await get_setup_status(db, user)


async def complete_setup(db: AsyncSession, user: User) -> TeacherSetupStatusOut:
    tp = await get_or_create_teacher_profile(db, user)
    if not tp.full_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="أدخل الاسم الكامل")

    subj_count = await db.execute(
        select(TeacherProfileSubject.id).where(TeacherProfileSubject.teacher_profile_id == tp.id).limit(1)
    )
    if not subj_count.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="اختر المواد التي تدرّسها")

    tp.setup_completed_at = datetime.now(timezone.utc)
    await db.flush()
    return await get_setup_status(db, user)
