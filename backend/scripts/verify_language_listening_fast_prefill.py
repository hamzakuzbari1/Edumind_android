"""Verify Phase 2.4 fast first response + background prefill."""

from __future__ import annotations

import asyncio
import time

from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageSkill
from app.models.language.tts_cache import LanguageLessonAudioCache
from app.services.language_listening_service import (
    TARGET_UNSEEN_LISTENING_POOL,
    _active_unseen_count,
    _adaptive_level,
    background_fill_listening_pool,
    next_listening,
)
from app.services.language_listening_prefill_task import background_prefill_listening_pool
from app.services.language_subscription_service import get_default_language

STUDENT_ID = 63


async def pool_size(db, student_id: int) -> tuple[int, int]:
    language = await get_default_language(db)
    level = await _adaptive_level(db, student_id=student_id, language_id=language.id)
    active = await _active_unseen_count(
        db, student_id=student_id, language_id=language.id, level=level
    )
    total = int(
        (
            await db.execute(
                select(func.count())
                .select_from(LanguageContentItem)
                .where(
                    LanguageContentItem.student_id == student_id,
                    LanguageContentItem.skill == LanguageSkill.listening,
                )
            )
        ).scalar()
        or 0
    )
    cached = int(
        (
            await db.execute(
                select(func.count())
                .select_from(LanguageLessonAudioCache)
                .join(
                    LanguageContentItem,
                    LanguageContentItem.id == LanguageLessonAudioCache.content_item_id,
                )
                .where(
                    LanguageContentItem.student_id == student_id,
                    LanguageContentItem.skill == LanguageSkill.listening,
                )
            )
        ).scalar()
        or 0
    )
    return active, total, cached, level


async def main() -> None:
    ok = True
    async with AsyncSessionLocal() as db:
        active0, total0, cache0, level = await pool_size(db, STUDENT_ID)
        print(f"Before: student={STUDENT_ID} level={level} active={active0} total={total0} audio_cached={cache0}")

    t0 = time.perf_counter()
    async with AsyncSessionLocal() as db:
        lesson, schedule = await next_listening(db, student_id=STUDENT_ID)
    sync_s = time.perf_counter() - t0
    print(f"\nSync next_listening: {sync_s:.2f}s schedule_background={schedule}")
    print(f"  lesson_id={lesson.get('id') if lesson else None} audio={lesson.get('audio_available') if lesson else None}")

    async with AsyncSessionLocal() as db:
        active1, total1, cache1, _ = await pool_size(db, STUDENT_ID)
        print(f"After sync: active={active1} total={total1} audio_cached={cache1}")

    ok = ok and lesson is not None
    ok = ok and schedule is True
    ok = ok and sync_s < 60.0
    if active0 == 0:
        ok = ok and total1 == total0 + 1  # only one lesson sync-generated

    # Simulate background prefill (as FastAPI BackgroundTasks would)
    bg_started = time.perf_counter()
    await background_prefill_listening_pool(student_id=STUDENT_ID)
    bg_s = time.perf_counter() - bg_started

    async with AsyncSessionLocal() as db:
        active2, total2, cache2, _ = await pool_size(db, STUDENT_ID)
        print(f"\nAfter background ({bg_s:.2f}s): active={active2} total={total2} audio_cached={cache2}")

    ok = ok and active2 >= TARGET_UNSEEN_LISTENING_POOL

    # Second request while pool full — should be fast, no extra rows
    t0 = time.perf_counter()
    async with AsyncSessionLocal() as db:
        lesson2, schedule2 = await next_listening(db, student_id=STUDENT_ID)
    warm_s = time.perf_counter() - t0
    async with AsyncSessionLocal() as db:
        active3, total3, _, _ = await pool_size(db, STUDENT_ID)
    print(f"\nSecond request: {warm_s:.2f}s schedule_background={schedule2} total_rows={total3}")
    ok = ok and lesson2 is not None
    ok = ok and schedule2 is False
    ok = ok and total3 == total2

    print("\nPASS" if ok else "\nFAIL")


if __name__ == "__main__":
    asyncio.run(main())
