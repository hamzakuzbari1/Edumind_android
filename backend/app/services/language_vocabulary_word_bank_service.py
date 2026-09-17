"""Fixed, per-level vocabulary word bank — serves each student's daily batch from the
pre-generated, deterministic word set for their CEFR level (see scripts/seed_vocabulary_word_bank.py)
instead of calling the LLM live on the request path.

Bank rows are level-scoped and shared by every student. The first time any student reaches a
given bank word, a LanguageContentItem is created for it (student_id=None, shared) and cached
forever — every later student who reaches the same (level, word) reuses that same content item,
so its lazily-generated image (get_or_create_word_image) is naturally shared too.
"""

from __future__ import annotations

import json

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progress import LanguageVocabularyProgress
from app.models.language.vocabulary_word_bank import LanguageVocabularyWordBank
from app.services.language_content_service import normalize_word
from app.services.language_engagement_service import upsert_vocabulary_from_lesson

CONTENT_TYPE = "vocabulary"


def _existing_content_item_query(*, language_id: int, level: LanguageLevel, lemma: str):
    return (
        select(LanguageContentItem)
        .where(
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.content_type == CONTENT_TYPE,
            LanguageContentItem.level == level,
            LanguageContentItem.body_json["word"].astext == lemma,
        )
        .limit(1)
    )


async def _get_or_create_content_item(
    db: AsyncSession, *, language_id: int, level: LanguageLevel, bank_word: LanguageVocabularyWordBank
) -> LanguageContentItem:
    """Get-or-create the one shared content item for this (level, word) — safe under concurrent
    callers. The plain check-then-insert this replaced had no DB-level backing, so two requests
    racing to illustrate the same never-before-seen word could each create their own row instead
    of sharing one; ON CONFLICT DO NOTHING against the partial unique index
    (uq_language_content_items_word_bank_word_level) makes the insert atomic, and a loser re-reads
    the winner's row rather than erroring.
    """
    lemma = normalize_word(bank_word.word)
    existing = (await db.execute(_existing_content_item_query(language_id=language_id, level=level, lemma=lemma))).scalar_one_or_none()
    if existing is not None:
        return existing

    body = {
        "word": lemma,
        "translation_ar": bank_word.translation_ar,
        "definition": bank_word.definition,
        "example": bank_word.example_sentence,
        "example_ar": bank_word.example_sentence_ar,
        "part_of_speech": bank_word.part_of_speech,
        "image_prompt": bank_word.image_prompt,
        "source": "word_bank",
    }
    # SQLAlchemy's on_conflict_do_nothing(index_elements=[...]) doesn't parenthesize a bare JSONB
    # astext expression in the ON CONFLICT target list, which Postgres's parser rejects outright
    # ("syntax error at or near '->>'") — raw SQL here guarantees the target list matches the
    # partial index (uq_language_content_items_word_bank_word_level) byte-for-byte.
    new_id = (
        await db.execute(
            text(
                """
                INSERT INTO language_content_items
                    (language_id, skill, level, content_type, title, body_json, is_published, sort_order)
                VALUES
                    (:language_id, :skill, :level, :content_type, :title, CAST(:body_json AS jsonb), true, :sort_order)
                ON CONFLICT (language_id, level, (body_json ->> 'word'))
                    WHERE content_type = 'vocabulary' AND body_json ->> 'source' = 'word_bank'
                DO NOTHING
                RETURNING id
                """
            ),
            {
                "language_id": language_id,
                "skill": LanguageSkill.reading.value,
                "level": level.value,
                "content_type": CONTENT_TYPE,
                "title": lemma,
                "body_json": json.dumps(body),
                "sort_order": bank_word.sort_order,
            },
        )
    ).scalar_one_or_none()
    if new_id is not None:
        await db.flush()
        return await db.get(LanguageContentItem, new_id)

    # Lost the race — a concurrent caller already inserted this word; read their row.
    winner = (await db.execute(_existing_content_item_query(language_id=language_id, level=level, lemma=lemma))).scalar_one_or_none()
    if winner is None:  # pragma: no cover - defensive, should be unreachable
        raise RuntimeError(f"word bank content item for {lemma!r}/{level.value} missing after conflict")
    return winner


async def serve_daily_words(
    db: AsyncSession, *, student_id: int, language_id: int, level: LanguageLevel, count: int
) -> list[tuple[LanguageVocabularyWordBank, LanguageContentItem]]:
    """Next `count` words from this level's fixed bank the student hasn't met yet (anti-join on
    LanguageVocabularyProgress.lemma, ordered by the bank's curated sort_order). Fewer than `count`
    rows back means the student has reached the end of their level's bank."""
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
    q = q.order_by(LanguageVocabularyWordBank.sort_order, LanguageVocabularyWordBank.id).limit(count)
    bank_words = (await db.execute(q)).scalars().all()

    lemmas: list[str] = []
    out: list[tuple[LanguageVocabularyWordBank, LanguageContentItem]] = []
    for bw in bank_words:
        item = await _get_or_create_content_item(db, language_id=language_id, level=level, bank_word=bw)
        out.append((bw, item))
        lemmas.append(normalize_word(bw.word))

    if lemmas:
        await upsert_vocabulary_from_lesson(db, student_id=student_id, language_id=language_id, lemmas=lemmas)
    return out
