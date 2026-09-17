"""Spaced repetition for vocabulary — SM-2 scheduling over LanguageVocabularyProgress.

This module is the SM-2 engine (`compute_sm2`) plus read helpers (`count_due`,
`get_vocabulary_stats`) and lesson-time ingestion (`upsert_vocabulary_with_sr`).
The single review/grading entry point lives in `language_vocabulary_service.review_vocabulary`,
which calls `compute_sm2` so the flashcard browser and the SM-2 schedule share one path.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.enums import LanguageVocabularyStatus
from app.models.language.progress import LanguageVocabularyProgress

VOCABULARY_CONTENT_TYPE = "vocabulary"


def compute_sm2(
    ease_factor: float, interval_days: int, repetition_number: int, quality: int
) -> tuple[float, int, int]:
    """SM-2: returns (ease_factor, interval_days, repetition_number). quality is 0-5."""
    if quality < 3:
        repetition_number = 0
        interval_days = 1
    else:
        if repetition_number == 0:
            interval_days = 1
        elif repetition_number == 1:
            interval_days = 6
        else:
            interval_days = round(interval_days * ease_factor)
        repetition_number += 1
    ease_factor = max(1.3, ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return ease_factor, interval_days, repetition_number


def _due_condition(now: datetime):
    """Items that are due: scheduled at/before now (or never scheduled) and not yet 'known'."""
    return (
        or_(
            LanguageVocabularyProgress.next_review_at <= now,
            LanguageVocabularyProgress.next_review_at.is_(None),
        ),
        LanguageVocabularyProgress.status != LanguageVocabularyStatus.known,
    )


async def count_due(db: AsyncSession, *, student_id: int, language_id: int) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(func.count())
        .select_from(LanguageVocabularyProgress)
        .where(
            LanguageVocabularyProgress.student_id == student_id,
            LanguageVocabularyProgress.language_id == language_id,
            *_due_condition(now),
        )
    )
    return int(result.scalar() or 0)


async def upsert_vocabulary_with_sr(
    db: AsyncSession, *, student_id: int, language_id: int, lemmas: list[str]
) -> None:
    """Insert new lemmas (scheduled due now) and backfill next_review_at on existing rows.

    Never resets SM-2 fields on existing items.
    """
    if not lemmas:
        return
    now = datetime.now(timezone.utc)
    for raw in lemmas:
        lemma = (raw or "").strip().lower()
        if not lemma or len(lemma) > 120:
            continue
        existing = await db.execute(
            select(LanguageVocabularyProgress).where(
                LanguageVocabularyProgress.student_id == student_id,
                LanguageVocabularyProgress.language_id == language_id,
                LanguageVocabularyProgress.lemma == lemma,
            )
        )
        row = existing.scalar_one_or_none()
        if row is not None:
            if row.next_review_at is None:
                row.next_review_at = now
            continue
        db.add(
            LanguageVocabularyProgress(
                student_id=student_id,
                language_id=language_id,
                lemma=lemma,
                status=LanguageVocabularyStatus.new,
                review_count=0,
                first_seen_at=now,
                mastery_score=0.0,
                next_review_at=now,
                interval_days=1,
                ease_factor=2.5,
                repetition_number=0,
            )
        )
    await db.flush()


async def get_vocabulary_stats(db: AsyncSession, *, student_id: int, language_id: int) -> dict:
    result = await db.execute(
        select(LanguageVocabularyProgress.status, func.count())
        .where(
            LanguageVocabularyProgress.student_id == student_id,
            LanguageVocabularyProgress.language_id == language_id,
        )
        .group_by(LanguageVocabularyProgress.status)
    )
    counts = {"new": 0, "learning": 0, "known": 0}
    for st, cnt in result.all():
        key = st.value if hasattr(st, "value") else str(st)
        counts[key] = int(cnt)
    due = await count_due(db, student_id=student_id, language_id=language_id)
    total = counts["new"] + counts["learning"] + counts["known"]
    return {
        "new": counts["new"],
        "learning": counts["learning"],
        "known": counts["known"],
        "total": total,
        "due_today": due,
    }
