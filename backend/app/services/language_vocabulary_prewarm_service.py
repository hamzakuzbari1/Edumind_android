"""Vocabulary image prewarm — nightly background job (Task 2, approved design).

Predicts which never-illustrated words active students will likely reach in their level's
word bank over the next `lookahead` positions (~1-2 days at the 10-word/day cap), and
pre-generates + caches their images ahead of time — so the lazy fallback on first view
(get_or_create_word_image, unchanged) rarely has to generate on the spot in front of a
student.

Purely additive:
- Reuses the exact get-or-create functions the lazy on-view path already calls
  (_get_or_create_content_item, get_or_create_word_image) — one source of truth for image
  generation and caching, not a second implementation.
- Deliberately never calls upsert_vocabulary_from_lesson. Pre-warming a word's image must
  not count as "serving" it to a student, or it would leak into their Review Bank
  (list_vocabulary, which is scoped to actually-served progress rows) before they've
  really reached it in a daily batch.
- Idempotent and safe to skip: images are cached forever on the shared LanguageContentItem
  once generated, regardless of whether this job runs on any given night.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel
from app.models.language.progress import LanguageVocabularyProgress
from app.models.language.vocabulary_ai_usage import LanguageVocabularyAiDailyUsage
from app.models.language.vocabulary_word_bank import LanguageVocabularyWordBank
from app.services.language_subscription_service import get_default_language
from app.services.language_vocabulary_image_service import get_or_create_word_image
from app.services.language_vocabulary_service import get_student_target_level
from app.services.language_vocabulary_word_bank_service import _get_or_create_content_item

logger = logging.getLogger(__name__)

LOOKAHEAD_WORDS = 20  # ~2 days of headroom at the existing 10-word/day daily-batch cap
ACTIVE_WINDOW_DAYS = 7  # "active student" = generated a daily batch at least once this recently
IMAGE_CONCURRENCY = 2  # mirrors the concurrency cap already used for image loading elsewhere


async def _active_student_ids(db: AsyncSession, *, since_days: int) -> list[int]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).date()
    rows = await db.execute(
        select(LanguageVocabularyAiDailyUsage.student_id)
        .where(LanguageVocabularyAiDailyUsage.usage_date >= cutoff)
        .distinct()
    )
    return list(rows.scalars().all())


async def _predicted_words_for_student(
    db: AsyncSession, *, student_id: int, language_id: int, level: LanguageLevel, lookahead: int
) -> list[LanguageVocabularyWordBank]:
    """The same anti-join serve_daily_words() uses to pick a student's next words — SELECT
    only, no side effects, so it's safe to call purely for prediction."""
    seen_lemmas = (
        await db.execute(
            select(LanguageVocabularyProgress.lemma).where(
                LanguageVocabularyProgress.student_id == student_id,
                LanguageVocabularyProgress.language_id == language_id,
            )
        )
    ).scalars().all()
    q = select(LanguageVocabularyWordBank).where(LanguageVocabularyWordBank.cefr_level == level)
    if seen_lemmas:
        q = q.where(LanguageVocabularyWordBank.word.notin_(seen_lemmas))
    q = q.order_by(LanguageVocabularyWordBank.sort_order, LanguageVocabularyWordBank.id).limit(lookahead)
    return list((await db.execute(q)).scalars().all())


async def _predict_target_words(
    db: AsyncSession, *, lookahead: int, active_window_days: int
) -> dict[LanguageLevel, dict[str, LanguageVocabularyWordBank]]:
    """level -> {word -> bank row}, deduped across every active student at that level."""
    language = await get_default_language(db)
    student_ids = await _active_student_ids(db, since_days=active_window_days)

    per_level: dict[LanguageLevel, dict[str, LanguageVocabularyWordBank]] = {}
    for student_id in student_ids:
        level = await get_student_target_level(db, student_id=student_id, language_id=language.id)
        words = await _predicted_words_for_student(
            db, student_id=student_id, language_id=language.id, level=level, lookahead=lookahead
        )
        bucket = per_level.setdefault(level, {})
        for w in words:
            bucket.setdefault(w.word, w)
    return per_level


async def _prewarm_one_word(language_id: int, level: LanguageLevel, bank_word: LanguageVocabularyWordBank) -> str:
    """Own AsyncSession per unit of work — AsyncSession isn't safe to share across
    concurrently-running coroutines, so each concurrent lane gets an independent one."""
    async with AsyncSessionLocal() as db:
        item = await _get_or_create_content_item(db, language_id=language_id, level=level, bank_word=bank_word)
        await db.commit()
        body = item.body_json or {}
        if body.get("image_url"):
            return "already_cached"
        try:
            url = await get_or_create_word_image(db, content_id=item.id)
        except Exception as exc:  # pragma: no cover - provider/network variance
            logger.warning("Prewarm image generation failed for %r: %s", bank_word.word, exc)
            return "failed"
        return "newly_generated" if url else "failed"


async def _run_limited(items: list, limit: int, worker) -> list:
    sem = asyncio.Semaphore(limit)

    async def bound(item):
        async with sem:
            return await worker(item)

    return await asyncio.gather(*(bound(item) for item in items))


async def run_nightly_image_prewarm(
    db: AsyncSession,
    *,
    lookahead: int = LOOKAHEAD_WORDS,
    active_window_days: int = ACTIVE_WINDOW_DAYS,
    concurrency: int = IMAGE_CONCURRENCY,
) -> dict:
    language = await get_default_language(db)
    per_level = await _predict_target_words(db, lookahead=lookahead, active_window_days=active_window_days)

    summary: dict[str, dict] = {}
    for level, words_by_lemma in per_level.items():
        bank_words = list(words_by_lemma.values())
        results = await _run_limited(
            bank_words, concurrency,
            lambda bw, _level=level: _prewarm_one_word(language.id, _level, bw),
        )
        summary[level.value] = {
            "candidate_words": len(results),
            "already_cached": results.count("already_cached"),
            "newly_generated": results.count("newly_generated"),
            "failed": results.count("failed"),
        }
        logger.info("Vocabulary image prewarm — %s: %s", level.value, summary[level.value])

    if not per_level:
        logger.info("Vocabulary image prewarm — no active students in the last %d day(s)", active_window_days)
    return summary
