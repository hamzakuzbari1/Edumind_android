"""Background personalized listening pool prefill — runs after /listening/next responds."""

from __future__ import annotations

import asyncio
import logging
import time

from app.db.session import AsyncSessionLocal
from app.services.language_listening_service import background_fill_listening_pool

logger = logging.getLogger(__name__)

_prefill_locks: dict[int, asyncio.Lock] = {}


async def background_prefill_listening_pool(*, student_id: int) -> None:
    """Fill the student's listening pool to TARGET without blocking the HTTP response."""
    lock = _prefill_locks.setdefault(student_id, asyncio.Lock())
    if lock.locked():
        logger.info("Listening background prefill already running student=%s", student_id)
        return

    started = time.perf_counter()
    async with lock:
        try:
            async with AsyncSessionLocal() as db:
                generated = await background_fill_listening_pool(db, student_id=student_id)
            logger.info(
                "Listening background prefill done student=%s generated=%s duration_s=%.2f",
                student_id,
                generated,
                time.perf_counter() - started,
            )
        except Exception:
            logger.warning(
                "Listening background prefill failed student=%s duration_s=%.2f",
                student_id,
                time.perf_counter() - started,
                exc_info=True,
            )
