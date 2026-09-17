"""Authorization for MediaObject download resolution (A6.0)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Course
from app.models.conversation import (
    ConversationMessage,
    ConversationMessageAttachment,
    ConversationParticipant,
)
from app.models.lesson import Lesson, LessonAsset
from app.models.media import MediaAccessScope, MediaObject, MediaStatus
from app.models.teacher_profile_cv import TeacherProfessionalDocument
from app.models.teacher_voice import TeacherVoiceSample
from app.models.user import User, UserRole
from app.services.subscription_access_service import student_has_active_enrollment


async def assert_media_download_allowed(
    db: AsyncSession,
    *,
    media: MediaObject,
    user: User,
) -> None:
    """Raise 403/404 when the actor may not resolve a download URL for this object."""
    if media.status == MediaStatus.deleted.value or media.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملف غير موجود")
    if media.status == MediaStatus.failed.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملف غير متاح")

    scope = (media.access_scope or "").strip().lower()
    # Explicit public assets are readable by any authenticated user.
    if scope == MediaAccessScope.public.value:
        return

    # Uploader always allowed.
    if media.uploaded_by_user_id and media.uploaded_by_user_id == user.id:
        return

    meta = media.metadata_json if isinstance(media.metadata_json, dict) else {}
    owner_id = meta.get("owner_user_id") or meta.get("uploaded_by_user_id")
    if owner_id and int(owner_id) == user.id:
        return

    if await _linked_lesson_access(db, media=media, user=user, meta=meta):
        return
    if await _linked_message_access(db, media=media, user=user):
        return
    if await _linked_teacher_document_access(db, media=media, user=user):
        return
    if await _linked_teacher_voice_access(db, media=media, user=user):
        return
    if await _linked_avatar_access(db, media=media, user=user):
        return

    # legacy_public local paths historically served via /uploads for entitled clients;
    # still require authentication (caller) and reject when no ownership link exists
    # for private-scoped objects.
    if scope == MediaAccessScope.legacy_public.value and media.storage_provider == "local":
        # Authenticated users may resolve legacy local public URLs (existing DEV behavior).
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ليس لديك صلاحية للوصول إلى هذا الملف")


async def _linked_lesson_access(
    db: AsyncSession,
    *,
    media: MediaObject,
    user: User,
    meta: dict,
) -> bool:
    asset = await db.scalar(
        select(LessonAsset)
        .where(LessonAsset.media_object_id == media.id)
        .options(selectinload(LessonAsset.lesson))
        .limit(1)
    )
    lesson: Lesson | None = asset.lesson if asset else None
    if lesson is None:
        lesson_id = meta.get("lesson_id")
        if lesson_id:
            lesson = await db.get(Lesson, int(lesson_id))
    if lesson is None:
        return False

    if user.role == UserRole.teacher and lesson.teacher_id == user.id:
        return True
    if user.role == UserRole.student and lesson.course_id:
        return await student_has_active_enrollment(db, user.id, lesson.course_id)
    return False


async def _linked_message_access(db: AsyncSession, *, media: MediaObject, user: User) -> bool:
    attachment = await db.scalar(
        select(ConversationMessageAttachment)
        .where(ConversationMessageAttachment.media_object_id == media.id)
        .limit(1)
    )
    if attachment is None:
        return False
    message = await db.get(ConversationMessage, attachment.message_id)
    if message is None:
        return False
    participant = await db.scalar(
        select(ConversationParticipant.id).where(
            ConversationParticipant.thread_id == message.thread_id,
            ConversationParticipant.user_id == user.id,
        )
    )
    return participant is not None


async def _linked_teacher_document_access(db: AsyncSession, *, media: MediaObject, user: User) -> bool:
    if user.role != UserRole.teacher:
        return False
    doc = await db.scalar(
        select(TeacherProfessionalDocument)
        .where(TeacherProfessionalDocument.media_object_id == media.id)
        .options(selectinload(TeacherProfessionalDocument.teacher_profile))
        .limit(1)
    )
    if doc is None or doc.teacher_profile is None:
        return False
    return getattr(doc.teacher_profile, "user_id", None) == user.id


async def _linked_teacher_voice_access(db: AsyncSession, *, media: MediaObject, user: User) -> bool:
    if user.role != UserRole.teacher:
        return False
    sample = await db.scalar(
        select(TeacherVoiceSample)
        .where(
            or_(
                TeacherVoiceSample.source_media_object_id == media.id,
                TeacherVoiceSample.preview_media_object_id == media.id,
            )
        )
        .options(selectinload(TeacherVoiceSample.teacher_profile))
        .limit(1)
    )
    if sample is None:
        profile = None
    else:
        profile = sample.teacher_profile
    if profile is None:
        return False
    return getattr(profile, "user_id", None) == user.id


async def _linked_avatar_access(db: AsyncSession, *, media: MediaObject, user: User) -> bool:
    owner = await db.scalar(select(User.id).where(User.avatar_media_object_id == media.id))
    if owner is None:
        course = await db.scalar(
            select(Course.id).where(
                or_(
                    Course.thumbnail_media_object_id == media.id,
                    Course.banner_media_object_id == media.id,
                )
            )
        )
        # Course marketing media: any authenticated user may resolve when scope is public;
        # for private course art, only linked teacher later — deny for now unless public handled above.
        return course is not None and (media.access_scope or "") == MediaAccessScope.public.value
    return owner == user.id or (media.access_scope or "") in {
        MediaAccessScope.public.value,
        MediaAccessScope.legacy_public.value,
    }
