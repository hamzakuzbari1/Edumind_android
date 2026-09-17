"""Teacher course and lesson management."""

from __future__ import annotations

import json
import random
import uuid
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import delete, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.academic_grades import ACADEMIC_GRADES, validate_academic_grade
from app.core.config import get_settings
from app.core.reference_catalog import ensure_reference_subjects
from app.models.catalog import (
    Course,
    Subject,
    TeacherProfile,
    TeacherProfileGrade,
    TeacherProfileSubject,
)
from app.models.lesson import ContentChunk, Lesson, LessonAsset, LessonAssetType, LessonContentType, LessonStatus
from app.models.enrollment import PaymentStatus, StudentCourseAccess
from app.models.progress import StudentLessonProgress
from app.models.quiz import QuizAttempt, QuizQuestion
from app.models.user import User
from app.schemas.teacher_courses import (
    LessonAssetOut,
    SubjectOptionOut,
    TeacherCourseCreate,
    TeacherCourseFormContextOut,
    TeacherCourseLessonOut,
    TeacherCourseOut,
    TeacherCourseUpdate,
    TeacherLessonPreviewOut,
    TeacherLessonUpdate,
)
from app.services.audit_service import log_audit
from app.services.lesson_assets_service import (
    asset_map_from_lesson,
    assets_public_urls,
    lesson_has_any_asset,
    paths_from_lesson,
    remove_lesson_asset,
    save_lesson_file,
    sync_lesson_legacy_columns,
)
from app.services.lesson_curated_insights_service import (
    apply_teacher_insight_overrides,
    clear_cached_insights_preserve_teacher,
)
from app.services.lesson_processor import process_lesson
from app.services.quiz_service import QUIZ_FOCUS_HINTS, generate_quiz_questions, is_lesson_text_too_short
from app.services.teacher_setup_service import get_or_create_teacher_profile

settings = get_settings()

LESSON_TYPE_LABELS = {
    "video": "فيديو",
    "pdf": "PDF",
    "homework": "واجب",
    "ai": "ذكاء اصطناعي",
}

MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _public_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http") or path.startswith("/uploads/"):
        return path
    try:
        rel = Path(path).resolve().relative_to(Path(settings.UPLOAD_DIR).resolve())
        return "/uploads/" + "/".join(rel.parts)
    except Exception:
        return None


async def _course_to_out(db: AsyncSession, course: Course) -> TeacherCourseOut:
    if course.subject is None:
        await db.refresh(course, ["subject"])
    count = await db.scalar(select(func.count()).select_from(Lesson).where(Lesson.course_id == course.id))
    return TeacherCourseOut(
        id=course.id,
        title=course.title,
        description=course.description,
        subject_name=course.subject.name_ar,
        subject_id=course.subject_id,
        grade=course.grade,
        price=course.price,
        currency=course.currency,
        thumbnail_url=_public_url(course.thumbnail_url),
        banner_url=_public_url(course.banner_url),
        is_published=course.is_published,
        lesson_count=int(count or 0),
    )


async def _ensure_teacher_teaching_links(
    db: AsyncSession, tp: TeacherProfile, subject_id: int, grade: int
) -> None:
    subj_link = await db.execute(
        select(TeacherProfileSubject.id).where(
            TeacherProfileSubject.teacher_profile_id == tp.id,
            TeacherProfileSubject.subject_id == subject_id,
        ).limit(1)
    )
    if not subj_link.scalar_one_or_none():
        db.add(TeacherProfileSubject(teacher_profile_id=tp.id, subject_id=subject_id))

    grade_link = await db.execute(
        select(TeacherProfileGrade.id).where(
            TeacherProfileGrade.teacher_profile_id == tp.id,
            TeacherProfileGrade.grade == grade,
        ).limit(1)
    )
    if not grade_link.scalar_one_or_none():
        db.add(TeacherProfileGrade(teacher_profile_id=tp.id, grade=grade))


def _save_course_media(
    user_id: int, course_id: int, prefix: str, content: bytes, filename: str
) -> str:
    upload_dir = Path(settings.UPLOAD_DIR) / f"teacher_{user_id}" / f"course_{course_id}"
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(filename or f"{prefix}.jpg").suffix or ".jpg"
    dest = upload_dir / f"{prefix}_{uuid.uuid4().hex}{ext}"
    dest.write_bytes(content)
    return str(dest)


async def get_form_context(db: AsyncSession, user: User, grade: int | None = None) -> TeacherCourseFormContextOut:
    await get_or_create_teacher_profile(db, user)
    await ensure_reference_subjects(db)

    # Always expose all school grades for course/lesson creation — not limited to
    # grades the teacher selected in their profile (that caused 7+12-only dropdowns).
    grades = list(ACADEMIC_GRADES)
    selected = grade if grade is not None else grades[0]
    if selected not in grades:
        validate_academic_grade(selected)
        grades = sorted(set(grades + [selected]))

    subj_result = await db.execute(
        select(Subject)
        .where(Subject.grade == selected, Subject.is_active.is_(True))
        .order_by(Subject.name_ar)
    )
    subjects = [
        SubjectOptionOut(id=s.id, name_ar=s.name_ar, grade=s.grade) for s in subj_result.scalars().all()
    ]
    return TeacherCourseFormContextOut(grades=grades, subjects=subjects)


async def _owned_course(db: AsyncSession, user: User, course_id: int) -> Course:
    tp = await get_or_create_teacher_profile(db, user)
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id, Course.teacher_profile_id == tp.id)
        .options(selectinload(Course.subject))
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدورة غير موجودة")
    return course


async def list_teacher_courses(db: AsyncSession, user: User) -> list[TeacherCourseOut]:
    tp = await get_or_create_teacher_profile(db, user)
    result = await db.execute(
        select(Course)
        .where(Course.teacher_profile_id == tp.id)
        .options(selectinload(Course.subject))
        .order_by(Course.grade, Course.title)
    )
    out: list[TeacherCourseOut] = []
    for course in result.scalars().all():
        out.append(await _course_to_out(db, course))
    return out


async def create_course(db: AsyncSession, user: User, body: TeacherCourseCreate) -> TeacherCourseOut:
    return await create_course_with_media(
        db,
        user,
        title=body.title,
        description=body.description,
        subject_id=body.subject_id,
        grade=body.grade,
        price=body.price,
        currency=body.currency,
        is_published=body.is_published,
        thumbnail_bytes=None,
        thumbnail_name=None,
        banner_bytes=None,
        banner_name=None,
    )


async def create_course_with_media(
    db: AsyncSession,
    user: User,
    *,
    title: str,
    description: str | None,
    subject_id: int,
    grade: int,
    price: float,
    currency: str = "SYP",
    is_published: bool,
    thumbnail_bytes: bytes | None,
    thumbnail_name: str | None,
    banner_bytes: bytes | None,
    banner_name: str | None,
) -> TeacherCourseOut:
    validate_academic_grade(grade)
    tp = await get_or_create_teacher_profile(db, user)
    await ensure_reference_subjects(db)

    subj = await db.get(Subject, subject_id)
    if not subj or subj.grade != grade:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="المادة غير متاحة لهذا الصف")

    course = Course(
        title=title.strip(),
        description=description,
        subject_id=subject_id,
        teacher_profile_id=tp.id,
        grade=grade,
        price=price,
        currency=currency or "SYP",
        is_published=is_published,
        is_active=True,
    )
    db.add(course)
    await db.flush()

    if thumbnail_bytes:
        if len(thumbnail_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail="صورة الغلاف كبيرة جداً")
        course.thumbnail_url = _save_course_media(
            user.id, course.id, "thumb", thumbnail_bytes, thumbnail_name or "thumb.jpg"
        )
    if banner_bytes:
        if len(banner_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail="صورة البانر كبيرة جداً")
        course.banner_url = _save_course_media(
            user.id, course.id, "banner", banner_bytes, banner_name or "banner.jpg"
        )

    await _ensure_teacher_teaching_links(db, tp, subject_id, grade)
    await db.flush()
    await log_audit(
        db,
        action="create",
        entity_type="course",
        entity_id=course.id,
        actor_user_id=user.id,
        new_values={"title": course.title, "grade": grade, "subject_id": subject_id},
    )
    await db.refresh(course, ["subject"])
    return await _course_to_out(db, course)


async def update_course(
    db: AsyncSession, user: User, course_id: int, body: TeacherCourseUpdate
) -> TeacherCourseOut:
    course = await _owned_course(db, user, course_id)
    tp = await get_or_create_teacher_profile(db, user)

    if body.subject_id is not None and body.subject_id != course.subject_id:
        subj = await db.get(Subject, body.subject_id)
        if not subj or subj.grade != course.grade:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="المادة غير متاحة لهذا الصف",
            )
        course.subject_id = body.subject_id
        await _ensure_teacher_teaching_links(db, tp, body.subject_id, course.grade)
        if body.title is None:
            course.title = subj.name_ar

    if body.title is not None:
        course.title = body.title.strip()
    if body.description is not None:
        course.description = body.description
    if body.price is not None:
        course.price = body.price
    if body.is_published is not None:
        course.is_published = body.is_published

    await db.flush()
    await db.refresh(course, ["subject"])
    await log_audit(
        db,
        action="update",
        entity_type="course",
        entity_id=course.id,
        actor_user_id=user.id,
        new_values=body.model_dump(exclude_unset=True),
    )
    return await _course_to_out(db, course)


def _lesson_out(lesson: Lesson) -> TeacherCourseLessonOut:
    sync_lesson_legacy_columns(lesson)
    urls = assets_public_urls(lesson)
    asset_rows: list[LessonAssetOut] = []
    for a in asset_map_from_lesson(lesson).values():
        at = a.asset_type.value if hasattr(a.asset_type, "value") else str(a.asset_type)
        asset_rows.append(
            LessonAssetOut(
                asset_type=at,
                url=urls.get(at) or _public_url(a.storage_path),
                original_filename=a.original_filename,
            )
        )
    if not asset_rows:
        for atype in ("video", "pdf", "homework", "audio"):
            if urls.get(atype):
                asset_rows.append(LessonAssetOut(asset_type=atype, url=urls[atype]))
    return TeacherCourseLessonOut(
        id=lesson.id,
        title=lesson.title,
        description=lesson.description or lesson.preview,
        video_url=urls.get("video"),
        pdf_url=urls.get("pdf"),
        homework_url=urls.get("homework"),
        audio_url=urls.get("audio"),
        assets=asset_rows,
        has_video=bool(urls.get("video")),
        has_pdf=bool(urls.get("pdf")),
        has_audio=bool(urls.get("audio")),
        sort_order=lesson.sort_order,
        status=lesson.status.value if hasattr(lesson.status, "value") else str(lesson.status),
        is_visible=lesson.is_visible,
    )


async def list_course_lessons(db: AsyncSession, user: User, course_id: int) -> list[TeacherCourseLessonOut]:
    await _owned_course(db, user, course_id)

    result = await db.execute(
        select(Lesson)
        .where(Lesson.course_id == course_id)
        .options(selectinload(Lesson.assets).selectinload(LessonAsset.media_object))
        .order_by(Lesson.sort_order, Lesson.id)
    )
    return [_lesson_out(l) for l in result.scalars().all()]


def _lesson_content_type(lesson: Lesson) -> str:
    ct = lesson.content_type
    if ct is None:
        return LessonContentType.video.value if lesson.video_url else LessonContentType.pdf.value
    return ct.value if hasattr(ct, "value") else str(ct)


async def _lesson_completion_percent(db: AsyncSession, course_id: int, lesson_id: int) -> int:
    from app.services.subscription_access_service import is_access_active

    access_rows = (
        await db.execute(
            select(StudentCourseAccess).where(
                StudentCourseAccess.course_id == course_id,
                StudentCourseAccess.payment_status == PaymentStatus.paid,
            )
        )
    ).scalars().all()
    active_ids = [a.student_id for a in access_rows if is_access_active(a)]
    if not active_ids:
        return 0
    done = int(
        (
            await db.scalar(
                select(func.count(distinct(StudentLessonProgress.student_id))).where(
                    StudentLessonProgress.lesson_id == lesson_id,
                    StudentLessonProgress.student_id.in_(active_ids),
                    StudentLessonProgress.completed_at.is_not(None),
                )
            )
            or 0
        )
    )
    return int(round((done / len(active_ids)) * 100))


async def get_course_lesson_detail(
    db: AsyncSession, user: User, course_id: int, lesson_id: int
) -> TeacherLessonPreviewOut:
    lesson = await _owned_lesson_in_course(db, user, course_id, lesson_id)
    course = await _owned_course(db, user, course_id)
    base = _lesson_out(lesson)
    ctype = _lesson_content_type(lesson)
    completion = await _lesson_completion_percent(db, course_id, lesson_id)
    sync_lesson_legacy_columns(lesson)
    paths = paths_from_lesson(lesson)
    chunk_count = int(
        await db.scalar(
            select(func.count()).select_from(ContentChunk).where(ContentChunk.lesson_id == lesson.id)
        )
        or 0
    )
    needs_reprocessing = bool(
        (paths.get("pdf") or paths.get("video"))
        and (lesson.status in (LessonStatus.draft, LessonStatus.error) or chunk_count == 0)
    )
    return TeacherLessonPreviewOut(
        **base.model_dump(),
        course_id=course_id,
        course_title=course.title,
        subject_name=course.subject.name_ar if course.subject else None,
        grade=course.grade,
        content_type=ctype,
        content_type_label=LESSON_TYPE_LABELS.get(ctype, ctype),
        preview=lesson.preview,
        created_at=lesson.created_at.isoformat() if lesson.created_at else None,
        updated_at=lesson.updated_at.isoformat() if lesson.updated_at else None,
        error_message=lesson.error_message,
        page_count=lesson.page_count,
        completion_percent=completion,
        needs_reprocessing=needs_reprocessing,
    )


async def _clear_lesson_ai_artifacts(db: AsyncSession, lesson: Lesson) -> None:
    await db.execute(delete(ContentChunk).where(ContentChunk.lesson_id == lesson.id))
    await db.execute(delete(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id))
    lesson.preview = None
    lesson.page_count = None
    lesson.error_message = None
    clear_cached_insights_preserve_teacher(lesson)


def _mark_lesson_needs_reprocessing(lesson: Lesson) -> None:
    sync_lesson_legacy_columns(lesson)
    paths = paths_from_lesson(lesson)
    if paths.get("pdf") or paths.get("video"):
        lesson.status = LessonStatus.draft
    else:
        lesson.status = LessonStatus.draft


async def update_course_lesson(
    db: AsyncSession,
    user: User,
    course_id: int,
    lesson_id: int,
    body: TeacherLessonUpdate,
) -> TeacherLessonPreviewOut:
    lesson = await _owned_lesson_in_course(db, user, course_id, lesson_id)
    if body.title is not None:
        lesson.title = body.title.strip()
    if body.description is not None:
        lesson.description = body.description.strip() or None
    if body.is_visible is not None:
        lesson.is_visible = body.is_visible
    if body.lesson_takeaways is not None or body.lesson_concepts is not None:
        apply_teacher_insight_overrides(
            lesson,
            takeaways=body.lesson_takeaways,
            concepts=body.lesson_concepts,
        )
    await db.flush()
    await log_audit(
        db,
        action="update",
        entity_type="lesson",
        entity_id=lesson.id,
        actor_user_id=user.id,
        new_values=body.model_dump(exclude_unset=True),
    )
    return await get_course_lesson_detail(db, user, course_id, lesson_id)


async def update_course_lesson_content(
    db: AsyncSession,
    user: User,
    course_id: int,
    lesson_id: int,
    *,
    title: str,
    description: str | None,
    is_visible: bool,
    remove_video: bool = False,
    remove_pdf: bool = False,
    remove_audio: bool = False,
    video_bytes: bytes | None = None,
    video_filename: str | None = None,
    pdf_bytes: bytes | None = None,
    pdf_filename: str | None = None,
    audio_bytes: bytes | None = None,
    audio_filename: str | None = None,
) -> tuple[TeacherLessonPreviewOut, bool]:
    """Update metadata and replace/remove lesson media. Returns (lesson, schedule_ai)."""
    lesson = await _owned_lesson_in_course(db, user, course_id, lesson_id)
    sync_lesson_legacy_columns(lesson)

    lesson.title = title.strip()
    lesson.description = (description or "").strip() or None
    lesson.is_visible = is_visible

    pdf_changed = False
    video_changed = False

    if remove_video:
        if paths_from_lesson(lesson).get("video"):
            await remove_lesson_asset(db, lesson, LessonAssetType.video)
            video_changed = True

    if remove_pdf:
        if paths_from_lesson(lesson).get("pdf"):
            await remove_lesson_asset(db, lesson, LessonAssetType.pdf)
            await _clear_lesson_ai_artifacts(db, lesson)
            pdf_changed = True

    if remove_audio:
        if paths_from_lesson(lesson).get("audio"):
            await remove_lesson_asset(db, lesson, LessonAssetType.audio)

    if video_bytes:
        if paths_from_lesson(lesson).get("video"):
            await remove_lesson_asset(db, lesson, LessonAssetType.video)
        await save_lesson_file(
            db,
            lesson,
            LessonAssetType.video,
            video_bytes,
            video_filename or "video.mp4",
            user_id=user.id,
            course_id=course_id,
            mime_type="video/mp4",
        )
        video_changed = True

    if pdf_bytes:
        if paths_from_lesson(lesson).get("pdf"):
            await remove_lesson_asset(db, lesson, LessonAssetType.pdf)
        await save_lesson_file(
            db,
            lesson,
            LessonAssetType.pdf,
            pdf_bytes,
            pdf_filename or "lesson.pdf",
            user_id=user.id,
            course_id=course_id,
            mime_type="application/pdf",
        )
        await _clear_lesson_ai_artifacts(db, lesson)
        pdf_changed = True

    if audio_bytes:
        if paths_from_lesson(lesson).get("audio"):
            await remove_lesson_asset(db, lesson, LessonAssetType.audio)
        await save_lesson_file(
            db,
            lesson,
            LessonAssetType.audio,
            audio_bytes,
            audio_filename or "audio.webm",
            user_id=user.id,
            course_id=course_id,
            mime_type="audio/webm",
        )

    sync_lesson_legacy_columns(lesson)
    _sync_lesson_content_type(lesson)

    if not lesson_has_any_asset(lesson):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يجب أن يحتوي الدرس على فيديو أو PDF أو ملف صوتي واحد على الأقل",
        )

    schedule_ai = False
    if pdf_changed or video_changed:
        await _clear_lesson_ai_artifacts(db, lesson)
        paths = paths_from_lesson(lesson)
        if paths.get("pdf") or paths.get("video"):
            _mark_lesson_needs_reprocessing(lesson)
            schedule_ai = True
        else:
            lesson.status = LessonStatus.processed
            lesson.error_message = None

    await db.flush()
    await log_audit(
        db,
        action="update_content",
        entity_type="lesson",
        entity_id=lesson.id,
        actor_user_id=user.id,
        new_values={
            "title": lesson.title,
            "is_visible": lesson.is_visible,
            "remove_video": remove_video,
            "remove_pdf": remove_pdf,
            "remove_audio": remove_audio,
            "replaced_video": bool(video_bytes),
            "replaced_pdf": bool(pdf_bytes),
            "replaced_audio": bool(audio_bytes),
        },
    )

    refreshed = await db.execute(
        select(Lesson).where(Lesson.id == lesson.id).options(
            selectinload(Lesson.assets).selectinload(LessonAsset.media_object)
        )
    )
    lesson = refreshed.scalar_one()
    detail = await get_course_lesson_detail(db, user, course_id, lesson_id)
    return detail, schedule_ai


async def _owned_lesson_in_course(
    db: AsyncSession, user: User, course_id: int, lesson_id: int
) -> Lesson:
    await _owned_course(db, user, course_id)
    result = await db.execute(
        select(Lesson)
        .where(
            Lesson.id == lesson_id,
            Lesson.course_id == course_id,
            Lesson.teacher_id == user.id,
        )
        .options(selectinload(Lesson.assets).selectinload(LessonAsset.media_object))
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدرس غير موجود")
    return lesson


def _sync_lesson_content_type(lesson: Lesson) -> None:
    if lesson.video_url and lesson.pdf_path:
        lesson.content_type = LessonContentType.video
    elif lesson.video_url:
        lesson.content_type = LessonContentType.video
    elif lesson.pdf_path:
        lesson.content_type = LessonContentType.pdf
    elif lesson.homework_path:
        lesson.content_type = LessonContentType.homework


async def add_video_lesson(
    db: AsyncSession,
    user: User,
    course_id: int,
    *,
    title: str,
    description: str | None,
    sort_order: int,
    video_bytes: bytes,
    filename: str,
    lesson_id: int | None = None,
) -> tuple[TeacherCourseLessonOut, bool]:
    course = await _owned_course(db, user, course_id)
    subj = await db.get(Subject, course.subject_id)

    if lesson_id:
        lesson = await _owned_lesson_in_course(db, user, course_id, lesson_id)
        if title.strip():
            lesson.title = title.strip()
        if description is not None:
            lesson.description = description
    else:
        lesson = Lesson(
            teacher_id=user.id,
            course_id=course_id,
            title=title.strip(),
            description=description,
            subject=subj.name_ar if subj else "مادة",
            grade=str(course.grade),
            sort_order=sort_order,
            status=LessonStatus.draft,
            is_visible=True,
        )
        db.add(lesson)
        await db.flush()

    await save_lesson_file(
        db,
        lesson,
        LessonAssetType.video,
        video_bytes,
        filename or "video.mp4",
        user_id=user.id,
        course_id=course_id,
        mime_type="video/mp4",
    )

    _sync_lesson_content_type(lesson)
    await db.flush()
    await _clear_lesson_ai_artifacts(db, lesson)
    _mark_lesson_needs_reprocessing(lesson)
    await db.flush()
    lesson = await _owned_lesson_in_course(db, user, course_id, lesson.id)
    return _lesson_out(lesson), True


async def add_pdf_lesson(
    db: AsyncSession,
    user: User,
    course_id: int,
    *,
    title: str,
    description: str | None,
    sort_order: int,
    pdf_bytes: bytes,
    filename: str,
    lesson_id: int | None = None,
    schedule_ai: bool = True,
) -> tuple[TeacherCourseLessonOut, bool]:
    """Save PDF and optionally queue the existing AI pipeline. Returns (lesson, should_schedule)."""
    course = await _owned_course(db, user, course_id)
    subj = await db.get(Subject, course.subject_id)

    if lesson_id:
        lesson = await _owned_lesson_in_course(db, user, course_id, lesson_id)
        if title.strip():
            lesson.title = title.strip()
        if description is not None:
            lesson.description = description
    else:
        lesson = Lesson(
            teacher_id=user.id,
            course_id=course_id,
            title=title.strip(),
            description=description,
            subject=subj.name_ar if subj else "مادة",
            grade=str(course.grade),
            sort_order=sort_order,
            status=LessonStatus.draft,
            is_visible=True,
        )
        db.add(lesson)
        await db.flush()

    await save_lesson_file(
        db,
        lesson,
        LessonAssetType.pdf,
        pdf_bytes,
        filename or "file.pdf",
        user_id=user.id,
        course_id=course_id,
        mime_type="application/pdf",
    )

    _sync_lesson_content_type(lesson)
    lesson.status = LessonStatus.draft
    lesson.error_message = None
    await db.flush()
    lesson = await _owned_lesson_in_course(db, user, course_id, lesson.id)
    return _lesson_out(lesson), schedule_ai


async def create_lesson_with_assets(
    db: AsyncSession,
    user: User,
    course_id: int,
    *,
    title: str,
    description: str | None,
    sort_order: int,
    video_bytes: bytes | None,
    video_filename: str | None,
    pdf_bytes: bytes | None,
    pdf_filename: str | None,
    external_video_url: str | None = None,
) -> tuple[TeacherCourseLessonOut, bool]:
    """One lesson row + lesson_assets (video and/or pdf) or external video URL."""
    if not video_bytes and not pdf_bytes and not external_video_url:
        raise HTTPException(status_code=400, detail="ارفع فيديو أو PDF أو أدخل رابط فيديو")

    if external_video_url and not external_video_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="رابط الفيديو غير صالح")

    course = await _owned_course(db, user, course_id)
    subj = await db.get(Subject, course.subject_id)

    lesson = Lesson(
        teacher_id=user.id,
        course_id=course_id,
        title=title.strip(),
        description=description,
        subject=subj.name_ar if subj else "مادة",
        grade=str(course.grade),
        sort_order=sort_order,
        is_visible=True,
        status=LessonStatus.draft,
    )
    db.add(lesson)
    await db.flush()

    if external_video_url and not video_bytes:
        lesson.video_url = external_video_url.strip()
        _sync_lesson_content_type(lesson)

    if video_bytes:
        await save_lesson_file(
            db,
            lesson,
            LessonAssetType.video,
            video_bytes,
            video_filename or "video.mp4",
            user_id=user.id,
            course_id=course_id,
        )

    schedule_ai = bool(video_bytes)
    if pdf_bytes:
        await save_lesson_file(
            db,
            lesson,
            LessonAssetType.pdf,
            pdf_bytes,
            pdf_filename or "lesson.pdf",
            user_id=user.id,
            course_id=course_id,
        )
        lesson.status = LessonStatus.draft
        lesson.error_message = None
        schedule_ai = True

    _sync_lesson_content_type(lesson)
    await db.flush()
    refreshed = await db.execute(
        select(Lesson).where(Lesson.id == lesson.id).options(
            selectinload(Lesson.assets).selectinload(LessonAsset.media_object)
        )
    )
    lesson = refreshed.scalar_one()
    await log_audit(
        db,
        action="create",
        entity_type="lesson",
        entity_id=lesson.id,
        actor_user_id=user.id,
        new_values={"course_id": course_id, "title": lesson.title, "has_pdf": bool(pdf_bytes)},
    )
    return _lesson_out(lesson), schedule_ai


# Backward-compatible alias
create_full_lesson = create_lesson_with_assets


async def add_homework_lesson(
    db: AsyncSession,
    user: User,
    course_id: int,
    *,
    title: str,
    description: str | None,
    sort_order: int,
    file_bytes: bytes,
    filename: str,
    lesson_id: int | None = None,
) -> TeacherCourseLessonOut:
    course = await _owned_course(db, user, course_id)
    subj = await db.get(Subject, course.subject_id)

    if lesson_id:
        lesson = await _owned_lesson_in_course(db, user, course_id, lesson_id)
        if title.strip():
            lesson.title = title.strip()
        if description is not None:
            lesson.description = description
    else:
        lesson = Lesson(
            teacher_id=user.id,
            course_id=course_id,
            title=title.strip(),
            description=description,
            subject=subj.name_ar if subj else "مادة",
            grade=str(course.grade),
            sort_order=sort_order,
            status=LessonStatus.processed,
            is_visible=True,
        )
        db.add(lesson)
        await db.flush()

    await save_lesson_file(
        db,
        lesson,
        LessonAssetType.homework,
        file_bytes,
        filename or "homework.pdf",
        user_id=user.id,
        course_id=course_id,
        mime_type="application/pdf",
    )

    _sync_lesson_content_type(lesson)
    await db.flush()
    lesson = await _owned_lesson_in_course(db, user, course_id, lesson.id)
    return _lesson_out(lesson)


async def add_smart_pdf_lesson(
    db: AsyncSession,
    user: User,
    course_id: int,
    *,
    title: str,
    description: str | None,
    sort_order: int,
    pdf_bytes: bytes,
    filename: str,
    lesson_id: int | None = None,
) -> tuple[TeacherCourseLessonOut, bool]:
    """Legacy alias — PDF uploads always use the real AI pipeline."""
    return await add_pdf_lesson(
        db,
        user,
        course_id,
        title=title,
        description=description,
        sort_order=sort_order,
        pdf_bytes=pdf_bytes,
        filename=filename,
        lesson_id=lesson_id,
        schedule_ai=True,
    )


async def process_course_lesson(db: AsyncSession, user: User, course_id: int, lesson_id: int) -> dict:
    lesson = await _owned_lesson_in_course(db, user, course_id, lesson_id)
    paths = paths_from_lesson(lesson)
    if not paths.get("pdf") and not paths.get("video"):
        raise HTTPException(status_code=400, detail="Upload a PDF or video first")
    lesson = await process_lesson(db, lesson)
    return {
        "lesson_id": lesson.id,
        "status": lesson.status.value,
        "message": lesson.error_message or "اكتملت المعالجة بنجاح",
    }


async def regenerate_course_lesson_quiz(
    db: AsyncSession, user: User, course_id: int, lesson_id: int
) -> dict:
    lesson = await _owned_lesson_in_course(db, user, course_id, lesson_id)
    if lesson.status != LessonStatus.processed:
        raise HTTPException(status_code=400, detail="عالج الدرس الذكي أولاً قبل إنشاء الكويز")

    result = await db.execute(
        select(Lesson)
        .where(Lesson.id == lesson.id)
        .options(selectinload(Lesson.chunks))
    )
    lesson = result.scalar_one()

    lesson_text = "\n\n".join(
        chunk.content for chunk in sorted(lesson.chunks, key=lambda x: x.chunk_index)
    )
    if is_lesson_text_too_short(lesson_text or lesson.preview or ""):
        raise HTTPException(status_code=400, detail="نص الدرس قصير جداً لإنشاء اختبار موثوق")

    old_result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.lesson_id == lesson.id)
        .order_by(QuizQuestion.sort_order)
    )
    old_questions = old_result.scalars().all()
    avoid_questions = [q.question for q in old_questions]
    target_count = max(settings.QUIZ_COUNT, 5)
    minimum_count = min(4, target_count)

    focus_pool = list(QUIZ_FOCUS_HINTS)
    random.shuffle(focus_pool)
    quiz_items: list[dict] = []
    for focus in focus_pool[:3]:
        generated = await generate_quiz_questions(
            lesson_text or lesson.preview or "",
            lesson.subject,
            lesson.grade,
            count=target_count,
            avoid_questions=avoid_questions,
            focus_hint=focus,
        )
        if len(generated) > len(quiz_items):
            quiz_items = generated
        if len(quiz_items) >= target_count:
            break

    if len(quiz_items) < minimum_count:
        generated = await generate_quiz_questions(
            lesson_text or lesson.preview or "",
            lesson.subject,
            lesson.grade,
            count=target_count,
            focus_hint=random.choice(focus_pool or list(QUIZ_FOCUS_HINTS)),
        )
        if len(generated) > len(quiz_items):
            quiz_items = generated

    if len(quiz_items) < minimum_count:
        raise HTTPException(
            status_code=400,
            detail=f"تعذر توليد اختبار متنوع من {minimum_count} أسئلة موثوقة من نص الدرس",
        )

    await db.execute(delete(QuizAttempt).where(QuizAttempt.lesson_id == lesson.id))
    await db.execute(delete(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id))
    for i, q in enumerate(quiz_items):
        db.add(
            QuizQuestion(
                lesson_id=lesson.id,
                question=q["question"],
                options_json=json.dumps(q["options"], ensure_ascii=False),
                correct_index=q["correct_index"],
                hint=q.get("hint"),
                sort_order=i,
            )
        )

    return {"lesson_id": lesson.id, "question_count": len(quiz_items), "message": "تم إنشاء الكويز بنجاح"}
