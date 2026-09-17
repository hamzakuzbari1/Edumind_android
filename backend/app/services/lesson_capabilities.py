"""Derived lesson capability flags from persisted DB state."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import ContentChunk, Lesson, LessonStatus
from app.models.quiz import QuizQuestion
from app.services.lesson_assets_service import lesson_has_any_asset, paths_from_lesson


def _status_value(lesson: Lesson) -> str:
    st = lesson.status
    return st.value if hasattr(st, "value") else str(st)


async def count_chunks(db: AsyncSession, lesson_id: int) -> int:
    return int(
        await db.scalar(
            select(func.count()).select_from(ContentChunk).where(ContentChunk.lesson_id == lesson_id)
        )
        or 0
    )


async def count_quiz_questions(db: AsyncSession, lesson_id: int) -> int:
    return int(
        await db.scalar(
            select(func.count()).select_from(QuizQuestion).where(QuizQuestion.lesson_id == lesson_id)
        )
        or 0
    )


async def build_lesson_capabilities(db: AsyncSession, lesson: Lesson) -> dict:
    paths = paths_from_lesson(lesson)
    has_video = bool(paths["video"])
    has_pdf = bool(paths["pdf"])
    has_homework = bool(paths["homework"])
    ai_status = _status_value(lesson)
    has_ai_source = has_pdf or has_video
    chunk_count = await count_chunks(db, lesson.id) if has_ai_source else 0
    quiz_count = await count_quiz_questions(db, lesson.id)

    processed = ai_status == LessonStatus.processed.value
    processing = ai_status == LessonStatus.processing.value
    errored = ai_status == LessonStatus.error.value
    stale_processing = False
    if processing and has_ai_source and chunk_count == 0 and lesson.updated_at:
        updated_at = lesson.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        stale_processing = (datetime.now(timezone.utc) - updated_at).total_seconds() > 20 * 60

    has_ai_chat = processed and chunk_count > 0
    has_generated_quiz = processed and quiz_count > 0

    return {
        "has_video": has_video,
        "has_pdf": has_pdf,
        "has_homework": has_homework,
        "has_ai_chat": has_ai_chat,
        "has_generated_quiz": has_generated_quiz,
        "ai_status": ai_status,
        "ai_ready": has_ai_chat,
        "quiz_ready": has_generated_quiz,
        "ai_processing": processing and not stale_processing,
        "ai_error": errored or stale_processing,
        "error_message": (
            lesson.error_message
            if errored
            else (
                "انقطعت معالجة الدرس قبل أن تكتمل. أعد تشغيل المعالجة من واجهة المعلم."
                if stale_processing
                else None
            )
        ),
        "chunk_count": chunk_count,
        "quiz_question_count": quiz_count,
    }


def resolve_lesson_content_type(lesson: Lesson) -> str:
    paths = paths_from_lesson(lesson)
    has_video = bool(paths["video"])
    has_pdf = bool(paths["pdf"])
    has_homework = bool(paths["homework"])

    if has_video and has_pdf:
        return "composite"
    if has_homework and not has_video and not has_pdf:
        return "homework"
    if has_pdf:
        return "pdf"
    if has_video:
        return "video"
    return "video"


def lesson_is_visible(lesson: Lesson) -> bool:
    if not lesson.is_visible:
        return False
    return lesson_has_any_asset(lesson)
