"""Background lesson AI processing via ai_jobs queue (no heavy work in HTTP handlers)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.ai_job import AiJob, AiJobStatus, AiJobType
from app.models.lesson import Lesson, LessonStatus
from app.services.ai_job_service import (
    enqueue_ai_job,
    mark_job_completed,
    mark_job_failed,
    mark_job_running,
)
from app.services.lesson_assets_service import paths_from_lesson, sync_lesson_legacy_columns
from app.services.lesson_processor import process_lesson

logger = logging.getLogger(__name__)

_running: set[int] = set()
STALE_JOB_SECONDS = 20 * 60


async def _recover_stale_lesson_job(db, lesson_id: int) -> None:
    """Mark orphaned running jobs failed after backend restart or hung whisper."""
    from sqlalchemy import text

    row = await db.execute(
        text(
            """
            SELECT id, status, started_at, created_at
            FROM ai_jobs
            WHERE lesson_id = :lesson_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"lesson_id": lesson_id},
    )
    job_row = row.mappings().first()
    if not job_row or job_row["status"] != AiJobStatus.running.value:
        return
    started = job_row["started_at"] or job_row["created_at"]
    if not started:
        return
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    age_s = (datetime.now(timezone.utc) - started).total_seconds()
    if age_s < STALE_JOB_SECONDS:
        return
    await db.execute(
        text(
            """
            UPDATE ai_jobs
            SET status = :failed, error_message = :err, completed_at = NOW()
            WHERE id = :job_id
            """
        ),
        {
            "failed": AiJobStatus.failed.value,
            "err": "processing_interrupted_or_timed_out",
            "job_id": job_row["id"],
        },
    )
    await db.execute(
        text(
            """
            UPDATE lessons
            SET status = :draft, error_message = :msg
            WHERE id = :lesson_id AND status = :processing
            """
        ),
        {
            "draft": LessonStatus.draft.value,
            "msg": "انقطعت معالجة الدرس — سيتم إعادة تشغيلها.",
            "lesson_id": lesson_id,
            "processing": LessonStatus.processing.value,
        },
    )
    logger.warning(
        "Recovered stale ai_job=%s lesson_id=%s age_s=%.0f",
        job_row["id"],
        lesson_id,
        age_s,
    )


async def _run_lesson_processing(lesson_id: int) -> None:
    if lesson_id in _running:
        return
    _running.add(lesson_id)
    job: AiJob | None = None
    try:
        async with AsyncSessionLocal() as db:
            await _recover_stale_lesson_job(db, lesson_id)
            await db.commit()

        async with AsyncSessionLocal() as db:
            job = await enqueue_ai_job(
                db,
                job_type=AiJobType.chatbot_context_generation,
                lesson_id=lesson_id,
                payload={"pipeline": ["extract_media", "chunk", "embed", "quiz"]},
            )
            await db.commit()
            job_id = job.id

        async with AsyncSessionLocal() as db:
            job = await db.get(AiJob, job_id)
            if not job:
                return
            await mark_job_running(db, job)
            await db.commit()

            result = await db.execute(
                select(Lesson).where(Lesson.id == lesson_id).options(selectinload(Lesson.assets))
            )
            lesson = result.scalar_one_or_none()
            if not lesson:
                await mark_job_failed(db, job, "lesson_not_found")
                await db.commit()
                return

            sync_lesson_legacy_columns(lesson)
            paths = paths_from_lesson(lesson)
            if not paths.get("pdf") and not paths.get("video"):
                await mark_job_failed(db, job, "no_pdf_or_video_asset")
                await db.commit()
                return

            await process_lesson(db, lesson)
            await mark_job_completed(
                db,
                job,
                result={"lesson_status": lesson.status, "lesson_id": lesson_id},
            )
            if lesson.course_id and lesson.is_visible:
                from app.services.integration_hooks import (
                    after_course_published,
                    notify_lesson_published,
                )

                await notify_lesson_published(
                    db,
                    course_id=lesson.course_id,
                    lesson_title=lesson.title,
                    lesson_id=lesson.id,
                )
                await after_course_published(db, lesson.course_id)
            await db.commit()
            logger.info(
                "Lesson %s AI processing finished status=%s job=%s",
                lesson_id,
                lesson.status,
                job_id,
            )
    except Exception as exc:
        logger.exception("Background lesson processing failed for lesson_id=%s", lesson_id)
        if job and job.id:
            try:
                async with AsyncSessionLocal() as db:
                    failed_job = await db.get(AiJob, job.id)
                    if failed_job:
                        await mark_job_failed(db, failed_job, str(exc)[:2000])
                        await db.commit()
            except Exception:
                logger.exception("Failed to mark ai_job %s as failed", job.id)
    finally:
        _running.discard(lesson_id)


def schedule_lesson_processing(lesson_id: int) -> None:
    """Enqueue PDF/AI pipeline — processed outside the request cycle."""
    asyncio.create_task(_run_lesson_processing(lesson_id))
