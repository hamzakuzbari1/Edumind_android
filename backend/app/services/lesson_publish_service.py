"""Unified lesson publish: course + assets + AI pipeline (teacher voice profile)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import HTTPException

from app.core.academic_grades import validate_academic_grade

from app.models.catalog import Course, Subject
from app.models.lesson import Lesson
from app.models.user import User
from app.schemas.lesson_publish import (
    LessonPublishOut,
    LessonPublishStatusOut,
    LessonPublishStepOut,
)
from app.schemas.teacher_courses import TeacherCourseCreate
from app.services import teacher_courses_service, teacher_voice_service
from app.services.lesson_capabilities import build_lesson_capabilities
from app.services.lesson_assets_service import sync_lesson_legacy_columns
from app.services.lesson_processing_tasks import schedule_lesson_processing
from app.services.teacher_setup_service import get_or_create_teacher_profile


async def _resolve_course(
    db: AsyncSession,
    user: User,
    *,
    grade: int,
    subject_id: int,
    course_id: int | None,
) -> Course:
    tp = await get_or_create_teacher_profile(db, user)
    await teacher_courses_service._ensure_teacher_teaching_links(db, tp, subject_id, grade)

    if course_id:
        return await teacher_courses_service._owned_course(db, user, course_id)

    result = await db.execute(
        select(Course)
        .where(
            Course.teacher_profile_id == tp.id,
            Course.subject_id == subject_id,
            Course.grade == grade,
        )
        .options(selectinload(Course.subject))
        .order_by(Course.created_at.desc())
        .limit(1)
    )
    course = result.scalar_one_or_none()
    if course:
        return course

    subj = await db.get(Subject, subject_id)
    if not subj:
        raise HTTPException(status_code=400, detail="المادة غير موجودة")

    created = await teacher_courses_service.create_course(
        db,
        user,
        TeacherCourseCreate(
            title=f"{subj.name_ar} — الصف {grade}",
            subject_id=subject_id,
            grade=grade,
            price=0,
            is_published=True,
        ),
    )
    return await teacher_courses_service._owned_course(db, user, created.id)


async def _teacher_voice_ready(db: AsyncSession, user: User) -> bool:
    profile = await teacher_voice_service.list_voice_samples(db, user)
    return bool(profile.get("has_ready_profile"))


async def publish_lesson(
    db: AsyncSession,
    user: User,
    *,
    grade: int,
    subject_id: int,
    title: str,
    description: str | None,
    sort_order: int,
    course_id: int | None,
    video_bytes: bytes | None,
    video_filename: str | None,
    pdf_bytes: bytes | None,
    pdf_filename: str | None,
) -> LessonPublishOut:
    if not title.strip():
        raise HTTPException(status_code=400, detail="عنوان الدرس مطلوب")
    validate_academic_grade(grade)
    if not video_bytes and not pdf_bytes:
        raise HTTPException(status_code=400, detail="ارفع فيديو أو PDF على الأقل")

    course = await _resolve_course(
        db, user, grade=grade, subject_id=subject_id, course_id=course_id
    )

    lesson_out, schedule_ai = await teacher_courses_service.create_lesson_with_assets(
        db,
        user,
        course.id,
        title=title,
        description=description,
        sort_order=sort_order,
        video_bytes=video_bytes,
        video_filename=video_filename,
        pdf_bytes=pdf_bytes,
        pdf_filename=pdf_filename,
    )

    voice_ready = await _teacher_voice_ready(db, user)
    await db.commit()

    if schedule_ai:
        schedule_lesson_processing(lesson_out.id)

    return LessonPublishOut(
        lesson_id=lesson_out.id,
        course_id=course.id,
        course_title=course.title,
        title=lesson_out.title,
        status=lesson_out.status,
        has_video=lesson_out.has_video,
        has_pdf=lesson_out.has_pdf,
        ai_processing_scheduled=schedule_ai,
        teacher_voice_ready=voice_ready,
        message="تم رفع الدرس — المعالجة الذكية تعمل في الخلفية",
    )


async def get_publish_status(
    db: AsyncSession, user: User, lesson_id: int
) -> LessonPublishStatusOut:
    result = await db.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id, Lesson.teacher_id == user.id)
        .options(selectinload(Lesson.assets))
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")

    sync_lesson_legacy_columns(lesson)
    caps = await build_lesson_capabilities(db, lesson)
    voice_ready = await _teacher_voice_ready(db, user)

    lesson_status = lesson.status.value if hasattr(lesson.status, "value") else str(lesson.status)
    has_ai_source = caps.get("has_pdf") or caps.get("has_video")
    ai_done = bool(caps.get("ai_ready")) if has_ai_source else lesson_status == "processed"
    ai_running = lesson_status == "processing"
    ai_error = lesson_status == "error"

    steps: list[LessonPublishStepOut] = [
        LessonPublishStepOut(key="saved", label="حفظ الدرس والملفات", done=True),
    ]

    if has_ai_source:
        steps.append(
            LessonPublishStepOut(
                key="lesson_ai",
                label="معالجة محتوى الدرس (محادثة + كويز)",
                done=ai_done,
                active=ai_running,
                error=lesson.error_message if ai_error else None,
            )
        )

    if ai_done and caps.get("has_generated_quiz"):
        steps.append(
            LessonPublishStepOut(key="quiz", label="توليد كويز الذكاء الاصطناعي", done=True)
        )
    elif has_ai_source and ai_running:
        steps.append(
            LessonPublishStepOut(key="quiz", label="توليد كويز الذكاء الاصطناعي", done=False, active=True)
        )

    if not voice_ready and has_ai_source:
        steps.append(
            LessonPublishStepOut(
                key="voice_hint",
                label="ملف الصوت — ارفع عينة من الملف الشخصي لتحسين الصوت الذكي",
                done=False,
            )
        )

    ai_source_ok = not has_ai_source or ai_done or ai_error
    complete = ai_source_ok and (ai_done or not has_ai_source)

    from app.services import ai_job_service

    ai_job = await ai_job_service.get_latest_lesson_job(db, lesson.id)

    return LessonPublishStatusOut(
        lesson_id=lesson.id,
        lesson_status=lesson_status,
        lesson_error=lesson.error_message,
        has_video=caps.get("has_video", False),
        has_pdf=caps.get("has_pdf", False),
        has_ai_chat=caps.get("has_ai_chat", False),
        has_generated_quiz=caps.get("has_generated_quiz", False),
        ai_ready=caps.get("ai_ready", False),
        teacher_voice_ready=voice_ready,
        steps=steps,
        complete=complete,
        ai_job_id=ai_job.id if ai_job else None,
        ai_job_status=ai_job.status if ai_job else None,
        ai_job_error=ai_job.error_message if ai_job else None,
    )
