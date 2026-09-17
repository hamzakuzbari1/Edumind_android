"""Enqueue AI work — workers process ai_jobs rows (no heavy work in HTTP handlers)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_job import AiJob, AiJobStatus, AiJobType


async def enqueue_ai_job(
    db: AsyncSession,
    *,
    job_type: AiJobType | str,
    lesson_id: int | None = None,
    payload: dict | None = None,
    commit: bool = False,
) -> AiJob:
    jt = job_type.value if isinstance(job_type, AiJobType) else str(job_type)
    job = AiJob(
        job_type=jt,
        status=AiJobStatus.pending.value,
        lesson_id=lesson_id,
        payload=payload or {},
    )
    db.add(job)
    await db.flush()
    if commit:
        await db.commit()
    return job


async def mark_job_running(db: AsyncSession, job: AiJob) -> None:
    job.status = AiJobStatus.running.value
    job.started_at = datetime.now(timezone.utc)
    await db.flush()


async def mark_job_completed(db: AsyncSession, job: AiJob, result: dict | None = None) -> None:
    job.status = AiJobStatus.completed.value
    job.result = result
    job.completed_at = datetime.now(timezone.utc)
    await db.flush()


async def mark_job_failed(db: AsyncSession, job: AiJob, error: str) -> None:
    job.status = AiJobStatus.failed.value
    job.error_message = error
    job.completed_at = datetime.now(timezone.utc)
    await db.flush()


async def get_job(db: AsyncSession, job_id: int) -> AiJob | None:
    return await db.get(AiJob, job_id)


async def get_latest_lesson_job(db: AsyncSession, lesson_id: int) -> AiJob | None:
    from sqlalchemy import select

    result = await db.execute(
        select(AiJob)
        .where(AiJob.lesson_id == lesson_id)
        .order_by(AiJob.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def retry_failed_job(db: AsyncSession, job: AiJob) -> AiJob:
    job.status = AiJobStatus.pending.value
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    job.result = None
    await db.flush()
    return job
