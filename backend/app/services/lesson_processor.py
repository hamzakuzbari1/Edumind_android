"""Full lesson processing pipeline: lesson media -> chunks -> voice -> quiz."""

import json
import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import ContentChunk, Lesson, LessonStatus
from app.models.catalog import TeacherProfile
from app.services.lesson_assets_service import paths_from_lesson, sync_lesson_legacy_columns
from app.models.quiz import QuizQuestion
from app.services.embedding_service import build_lesson_faiss_index
from app.services.lesson_curated_insights_service import curate_and_cache_lesson_insights
from app.services.pdf_service import chunk_text, extract_text_from_pdf_async
from app.services.quiz_service import generate_quiz_questions
from app.services.voice_service import build_persona_prompt, transcribe_audio, transcribe_lesson_video
from app.services.video_transcription.errors import VideoTranscriptionError

logger = logging.getLogger(__name__)


async def process_lesson(db: AsyncSession, lesson: Lesson) -> Lesson:
    lesson.status = LessonStatus.processing
    await db.commit()

    try:
        sync_lesson_legacy_columns(lesson)
        paths = paths_from_lesson(lesson)
        pdf_path = paths.get("pdf")
        video_path = paths.get("video")
        if not pdf_path and not video_path:
            raise ValueError("ارفع PDF أو فيديو أولاً")

        full_text = ""
        page_count = None
        pages_meta = []
        source_chunks: list[tuple[str, dict]] = []
        if pdf_path:
            try:
                full_text, page_count, pages_meta = await extract_text_from_pdf_async(pdf_path)
            except Exception as exc:
                if not video_path:
                    raise
                logger.warning("PDF extraction failed for lesson %s, using video: %s", lesson.id, exc)
        if pdf_path and not video_path and not full_text.strip():
            raise ValueError("تعذر استخراج نص من PDF — جرّب ملفاً آخر")

        source_texts = []
        if full_text.strip():
            source_texts.append(full_text)
            for idx, content in enumerate(chunk_text(full_text)):
                page_hint = pages_meta[min(idx, len(pages_meta) - 1)] if pages_meta else {}
                source_chunks.append((content, {"source": "pdf", "page_hint": page_hint}))
        if video_path:
            video_transcript = ""
            try:
                video_transcript = (
                    await transcribe_lesson_video(
                        video_path,
                        subject=getattr(lesson, "subject", None),
                    )
                    or ""
                ).strip()
            except VideoTranscriptionError as exc:
                if not pdf_path:
                    raise ValueError(exc.user_message) from exc
                logger.warning(
                    "Video transcription failed for lesson %s category=%s",
                    lesson.id,
                    exc.category,
                )
            if video_transcript:
                video_text = video_transcript
                source_texts.append(video_text)
                for idx, content in enumerate(chunk_text(video_text)):
                    source_chunks.append((content, {"source": "video", "segment": idx + 1}))
            elif not pdf_path:
                raise ValueError("تعذر استخراج نص من صوت الفيديو")
            else:
                logger.warning("Video transcript was empty for lesson %s", lesson.id)

        full_text = "\n\n".join(source_texts).strip()
        if not full_text:
            raise ValueError("Could not extract lesson text from the uploaded assets")

        lesson.page_count = page_count
        lesson.preview = full_text[:280] + ("…" if len(full_text) > 280 else "")
        if lesson.title == "درس جديد" or not lesson.title:
            lesson.title = _guess_title(full_text, lesson.subject)

        transcript = ""
        voice_path = lesson.voice_path
        if not voice_path:
            from app.services.teacher_voice_service import get_ready_voice_path_for_teacher

            voice_path = await get_ready_voice_path_for_teacher(db, lesson.teacher_id)
        if voice_path:
            transcript = await transcribe_audio(voice_path)

        persona = lesson.persona_prompt
        if not persona:
            from app.services.teacher_voice_service import get_ready_persona_for_teacher

            persona = await get_ready_persona_for_teacher(db, lesson.teacher_id)
        if persona:
            lesson.persona_prompt = persona
        elif transcript:
            lesson.persona_prompt = await build_persona_prompt(
                transcript, lesson.subject, lesson.grade
            )
        else:
            lesson.persona_prompt = await build_persona_prompt("", lesson.subject, lesson.grade)

        await db.execute(delete(ContentChunk).where(ContentChunk.lesson_id == lesson.id))
        if not source_chunks:
            source_chunks = [(content, {"source": "lesson"}) for content in chunk_text(full_text)]

        text_chunks = [content for content, _ in source_chunks]
        for idx, (content, metadata) in enumerate(source_chunks):
            meta = json.dumps(metadata, ensure_ascii=False)
            db.add(
                ContentChunk(
                    lesson_id=lesson.id,
                    chunk_index=idx,
                    content=content,
                    metadata_json=meta,
                )
            )

        await build_lesson_faiss_index(lesson.id, text_chunks)

        teacher_profile = None
        if lesson.teacher_id:
            profile_result = await db.execute(
                select(TeacherProfile).where(TeacherProfile.user_id == lesson.teacher_id)
            )
            teacher_profile = profile_result.scalar_one_or_none()
        await curate_and_cache_lesson_insights(db, lesson, full_text, teacher_profile)

        await db.execute(delete(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id))
        quiz_items = await generate_quiz_questions(full_text, lesson.subject, lesson.grade)
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

        lesson.status = LessonStatus.processed
        lesson.error_message = None
    except Exception as exc:
        logger.exception("Lesson processing failed: %s", exc)
        lesson.status = LessonStatus.error
        lesson.error_message = str(exc)

    await db.commit()
    await db.refresh(lesson)
    return lesson


def _guess_title(text: str, subject: str) -> str:
    first_line = text.split("\n", 1)[0].strip()[:80]
    if len(first_line) > 10:
        return first_line
    return f"درس {subject}"
