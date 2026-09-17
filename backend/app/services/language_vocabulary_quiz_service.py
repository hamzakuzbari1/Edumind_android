"""Daily vocabulary quiz (Task 4, approved design) — spelling + pronunciation checks over
words the student has ALREADY learned, never new/unserved ones.

Word selection: primarily today's actually-served batch (a LanguageVocabularyProgress row
is only ever created the first time a lemma is served to a student, so "created today" IS
"today's daily batch" — no separate tracking needed), topped up with due words and then any
other already-learned word if today's batch was smaller than the target size.

Spelling is graded server-side (the target word is never sent to the client until after it
submits a guess, so the quiz can't be trivially read off the network payload). Pronunciation
reuses the exact same assess_word_pronunciation() pipeline the vocabulary card's "Say it"
button already calls — no separate implementation.

Results are logged as a LanguageActivityLog event (event_type='vocabulary_quiz_completed'),
mirroring how the existing daily fill-in-the-blanks challenge records itself
(submit_vocabulary_challenge / record_challenge_results) — the quiz never touches the SM-2
flashcard schedule, since a quiz answer is a different kind of evidence than a flashcard
grade.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.models.language.engagement import LanguageActivityLog
from app.models.language.enums import LanguageSkill, LanguageVocabularyStatus
from app.models.language.progress import LanguageVocabularyProgress
from app.services.language_content_service import normalize_word
from app.services.language_engagement_service import record_activity

CONTENT_TYPE = "vocabulary"
DAILY_QUIZ_TARGET_SIZE = 10  # matches the 10-word daily new-word batch
QUIZ_EVENT_TYPE = "vocabulary_quiz_completed"


def _edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr = [i] + [0] * n
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[n]


def _mask_word(example: str, word: str) -> str:
    import re

    if not example or not word:
        return example or ""
    return re.sub(re.escape(word), "_____", example, flags=re.IGNORECASE)


def _is_due(progress: LanguageVocabularyProgress, now: datetime) -> bool:
    if progress.status == LanguageVocabularyStatus.known:
        return False
    nra = progress.next_review_at
    if nra is None:
        return True
    if nra.tzinfo is None:
        nra = nra.replace(tzinfo=timezone.utc)
    return nra <= now


async def _todays_served_lemmas(db: AsyncSession, *, student_id: int, language_id: int) -> list[str]:
    """A progress row is only ever created the first time a lemma is served to a student
    (upsert_vocabulary_from_lesson), so first_seen_at falling on today IS "today's batch"."""
    today = datetime.now(timezone.utc).date()
    rows = await db.execute(
        select(LanguageVocabularyProgress.lemma).where(
            LanguageVocabularyProgress.student_id == student_id,
            LanguageVocabularyProgress.language_id == language_id,
            func.date(LanguageVocabularyProgress.first_seen_at) == today,
        )
    )
    return list(rows.scalars().all())


async def _fallback_learned_lemmas(
    db: AsyncSession, *, student_id: int, language_id: int, exclude: list[str], limit: int
) -> list[str]:
    """Due words first, then any other already-learned (status != new) word — never new ones."""
    if limit <= 0:
        return []
    q = select(LanguageVocabularyProgress).where(
        LanguageVocabularyProgress.student_id == student_id,
        LanguageVocabularyProgress.language_id == language_id,
        LanguageVocabularyProgress.status != LanguageVocabularyStatus.new,
    )
    if exclude:
        q = q.where(LanguageVocabularyProgress.lemma.notin_(exclude))
    rows = (await db.execute(q)).scalars().all()
    now = datetime.now(timezone.utc)
    due = [p.lemma for p in rows if _is_due(p, now)]
    rest = [p.lemma for p in rows if p.lemma not in due]
    random.shuffle(due)
    random.shuffle(rest)
    return (due + rest)[:limit]


async def _content_item_for_lemma(db: AsyncSession, *, language_id: int, lemma: str) -> LanguageContentItem | None:
    return (
        await db.execute(
            select(LanguageContentItem)
            .where(
                LanguageContentItem.language_id == language_id,
                LanguageContentItem.content_type == CONTENT_TYPE,
                LanguageContentItem.is_published.is_(True),
                func.lower(LanguageContentItem.body_json["word"].astext) == lemma,
            )
            .order_by(LanguageContentItem.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _already_completed_today(db: AsyncSession, *, student_id: int) -> bool:
    today = datetime.now(timezone.utc).date()
    count = await db.execute(
        select(func.count()).select_from(LanguageActivityLog).where(
            LanguageActivityLog.student_id == student_id,
            LanguageActivityLog.event_type == QUIZ_EVENT_TYPE,
            func.date(LanguageActivityLog.created_at) == today,
        )
    )
    return bool(count.scalar_one())


async def build_daily_quiz(
    db: AsyncSession, *, student_id: int, language_id: int, target_size: int = DAILY_QUIZ_TARGET_SIZE
) -> dict:
    served_today = await _todays_served_lemmas(db, student_id=student_id, language_id=language_id)
    lemmas = list(served_today[:target_size])
    if len(lemmas) < target_size:
        topup = await _fallback_learned_lemmas(
            db, student_id=student_id, language_id=language_id,
            exclude=lemmas, limit=target_size - len(lemmas),
        )
        lemmas.extend(topup)

    items = []
    for lemma in lemmas:
        item = await _content_item_for_lemma(db, language_id=language_id, lemma=lemma)
        if not item:
            continue
        body = item.body_json or {}
        items.append({
            "item_id": item.id,
            "definition": body.get("definition") or "",
            "example_masked": _mask_word(body.get("example") or "", lemma),
        })

    return {
        "items": items,
        "total": len(items),
        "already_completed_today": await _already_completed_today(db, student_id=student_id),
    }


async def check_quiz_spelling(db: AsyncSession, *, language_id: int, content_id: int, guess: str) -> dict:
    item = await db.get(LanguageContentItem, content_id)
    if not item or item.language_id != language_id or item.content_type != CONTENT_TYPE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz word not found")
    correct_word = normalize_word((item.body_json or {}).get("word") or "")
    guess_norm = normalize_word(guess)
    if not correct_word:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid quiz item")

    correct = guess_norm == correct_word
    near_miss = (not correct) and guess_norm and _edit_distance(guess_norm, correct_word) <= 2
    return {"correct": correct, "near_miss": bool(near_miss), "correct_word": correct_word}


async def record_quiz_completion(
    db: AsyncSession, *, student_id: int, language_id: int, results: list[dict]
) -> dict:
    spelling_total = len(results)
    spelling_correct = sum(1 for r in results if r.get("spelling_correct"))
    pron_scores = [r["pronunciation_score"] for r in results if r.get("pronunciation_score") is not None]
    pron_avg = (sum(pron_scores) / len(pron_scores)) if pron_scores else 0.0

    if spelling_total:
        await record_activity(
            db,
            student_id=student_id,
            language_id=language_id,
            event_type=QUIZ_EVENT_TYPE,
            skill=LanguageSkill.reading,
            payload_json={
                "spelling_correct": spelling_correct,
                "spelling_total": spelling_total,
                "pronunciation_average": round(pron_avg, 1),
            },
        )

    return {
        "spelling_correct": spelling_correct,
        "spelling_total": spelling_total,
        "pronunciation_average": round(pron_avg, 1),
        "recorded": bool(spelling_total),
    }
