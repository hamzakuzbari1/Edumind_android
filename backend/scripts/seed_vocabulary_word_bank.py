"""Seed the fixed, per-level vocabulary word bank (Phase 7).

Generates a deterministic, curated word set per CEFR level via Claude, in batches, and inserts
it into language_vocabulary_word_bank (unique on word + cefr_level). Idempotent and resumable:
re-running tops each level up to its target count, skipping words already in the bank
(ON CONFLICT DO NOTHING is the real dedup guard — the in-prompt "avoid" list is just a hint to
reduce wasted generations).

Images are NOT pre-generated here — they stay on the existing lazy, cache-forever path
(get_or_create_word_image, triggered on first view of the LanguageContentItem the word bank
service creates), so this script only needs a database, no image-generation quota.

Usage (from backend/):
    python scripts/seed_vocabulary_word_bank.py                 # dry run: 1 preview batch/level
    python scripts/seed_vocabulary_word_bank.py --apply          # actually seed, all levels
    python scripts/seed_vocabulary_word_bank.py --apply --level A1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel
from app.models.language.vocabulary_word_bank import LanguageVocabularyWordBank
from app.services.ai_service import generate_llm_json
from app.services.language_content_service import normalize_word
from app.services.language_conversation_prompts import level_calibration_line

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_vocabulary_word_bank")

# Ascending distribution: higher levels cover a broader vocabulary range (A1 core survival
# vocabulary is inherently smaller than C2's near-native range), confirmed with the product owner.
TARGET_PER_LEVEL: dict[LanguageLevel, int] = {
    LanguageLevel.A1: 150,
    LanguageLevel.A2: 180,
    LanguageLevel.B1: 210,
    LanguageLevel.B2: 240,
    LanguageLevel.C1: 270,
    LanguageLevel.C2: 300,
}

BATCH_SIZE = 15
MAX_ATTEMPTS_PER_LEVEL = 80  # safety valve against infinite collision loops
MAX_CONSECUTIVE_EMPTY_BATCHES = 5  # abort fast on a systemic failure (e.g. API quota), not word collisions

_SYSTEM = (
    "You are an expert curriculum designer building a fixed CEFR vocabulary word list for an "
    "English-learning platform whose students are Syrian secondary-school learners. Write natural "
    "English at the requested CEFR level. Output is ENGLISH ONLY (never Arabic) except the "
    "translation_ar and example_sentence_ar fields. Return ONLY valid JSON — no markdown, no code fences."
)

# A manual audit of 20 generated flashcard images found the failures cluster in one place: the
# model defaults to an easy metonym (a labeled diagram, a random object standing in for an
# abstract quality) instead of dramatizing the definition itself. This instruction is deliberately
# directive to close that gap — see the seeding report for the before/after examples.
_IMAGE_PROMPT_INSTRUCTION = (
    "ONE concrete, unambiguous scene (under 20 words) that directly DRAMATIZES this exact "
    "definition through a person's visible action, facial expression, or body language — not a "
    "diagram, chart, icon pair, split-panel comparison, or anything with labels. For abstract "
    "nouns/adjectives (e.g. 'reliable', 'patience', 'connection'), show a person clearly "
    "experiencing or demonstrating the quality in a situation — never an inanimate object standing "
    "in for the idea (e.g. NOT 'a wifi router' for reliable; INSTEAD 'a friend arriving exactly on "
    "time every single day, being greeted with relief'). Never mention any text, words, letters, "
    "numbers, signs, or labels appearing in the scene"
)


def _parse_words(raw: str) -> list[dict]:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return []
    try:
        data = json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return []
    words = data.get("words") if isinstance(data, dict) else None
    return [w for w in words if isinstance(w, dict)] if isinstance(words, list) else []


async def _existing_words(db, level: LanguageLevel) -> set[str]:
    rows = (
        await db.execute(
            select(LanguageVocabularyWordBank.word).where(LanguageVocabularyWordBank.cefr_level == level)
        )
    ).scalars().all()
    return set(rows)


async def _next_sort_order(db, level: LanguageLevel) -> int:
    top = (
        await db.execute(
            select(func.max(LanguageVocabularyWordBank.sort_order)).where(
                LanguageVocabularyWordBank.cefr_level == level
            )
        )
    ).scalar_one()
    return int(top or 0) + 1


async def _generate_batch(level: LanguageLevel, *, size: int, avoid_sample: list[str]) -> list[dict]:
    avoid_line = (
        f" Do NOT repeat any of these words already in the bank: {', '.join(avoid_sample)}."
        if avoid_sample
        else ""
    )
    prompt = (
        f"Generate exactly {size} DISTINCT English vocabulary words for a {level.value} CEFR word bank.\n"
        "Cover a broad, natural mix of everyday topics (school, family, food, technology, nature, work, "
        "travel, emotions, health, hobbies, city life) so the list feels like a real curriculum, not a "
        "random word dump. Prefer common, high-utility words a learner will actually encounter." + avoid_line
        + level_calibration_line(level.value)
        + "\nReturn ONLY JSON with EXACTLY this shape: "
        '{"words": [ { "word", "part_of_speech" (noun/verb/adjective/adverb/...), '
        "\"definition\" (simple English definition at the learner's level), "
        '"example_sentence" (a natural English sentence using the word), '
        '"example_sentence_ar" (an Arabic translation of that EXACT example_sentence — same meaning, natural Arabic), '
        '"translation_ar" (Arabic translation of the WORD itself, not the sentence), '
        '"image_prompt" (' + _IMAGE_PROMPT_INSTRUCTION + '), '
        '"topic" (one short topic tag, e.g. "food", "travel", "school") }, ... ] }'
    )
    raw = await generate_llm_json(prompt, system=_SYSTEM, temperature=0.6, max_output_tokens=6500)
    return _parse_words(raw)


def _row_from_word(w: dict, *, level: LanguageLevel, lemma: str, sort_order: int) -> dict:
    return {
        "cefr_level": level,
        "word": lemma,
        "part_of_speech": str(w.get("part_of_speech") or "").strip()[:40],
        "translation_ar": str(w.get("translation_ar") or "").strip(),
        "definition": str(w.get("definition") or "").strip(),
        "example_sentence": str(w.get("example_sentence") or "").strip(),
        "example_sentence_ar": str(w.get("example_sentence_ar") or "").strip(),
        "image_prompt": str(w.get("image_prompt") or "").strip(),
        "topic": str(w.get("topic") or "").strip()[:60],
        "sort_order": sort_order,
    }


async def seed_level(db, level: LanguageLevel, *, target: int, apply: bool) -> dict:
    existing = await _existing_words(db, level)
    have = len(existing)
    needed = max(0, target - have)
    logger.info("%s: %d/%d already in bank (%d needed)", level.value, have, target, needed)
    if needed == 0:
        return {"level": level.value, "before": have, "added": 0, "after": have, "target": target}

    if not apply:
        # Dry run: a single small preview batch (not the full target) so this stays cheap/fast —
        # ON CONFLICT DO NOTHING at --apply time is the real dedup guard, not this preview.
        sample = await _generate_batch(level, size=min(5, needed), avoid_sample=list(existing)[-60:])
        for w in sample:
            logger.info("  [dry-run sample] %s: %r (%s)", level.value, w.get("word"), w.get("part_of_speech"))
        return {"level": level.value, "before": have, "added": 0, "after": have, "target": target, "needed": needed}

    added = 0
    attempts = 0
    consecutive_empty = 0
    sort_order = await _next_sort_order(db, level)
    # Full existing set, not just a trailing sample — with the target this size (up to 300), an
    # incomplete hint let the model keep re-suggesting already-banked words as the level filled up,
    # wasting attempts and stalling well short of target.
    avoid_sample = list(existing)

    while have + added < target and attempts < MAX_ATTEMPTS_PER_LEVEL:
        attempts += 1
        remaining = target - (have + added)
        batch = await _generate_batch(level, size=min(BATCH_SIZE, remaining + 5), avoid_sample=avoid_sample)
        if not batch:
            consecutive_empty += 1
            logger.warning("%s: empty/unparseable batch on attempt %d, retrying", level.value, attempts)
            if consecutive_empty >= MAX_CONSECUTIVE_EMPTY_BATCHES:
                logger.error(
                    "%s: %d consecutive empty batches — likely a systemic failure (e.g. API quota), "
                    "stopping this level early at %d/%d",
                    level.value, consecutive_empty, have + added, target,
                )
                break
            continue
        consecutive_empty = 0

        rows = []
        for w in batch:
            lemma = normalize_word(str(w.get("word") or ""))[:80]
            if not lemma or lemma in existing:
                continue
            existing.add(lemma)
            rows.append(_row_from_word(w, level=level, lemma=lemma, sort_order=sort_order))
            sort_order += 1
            if have + added + len(rows) >= target:
                break

        if not rows:
            continue

        stmt = pg_insert(LanguageVocabularyWordBank).values(rows).on_conflict_do_nothing(
            index_elements=["word", "cefr_level"]
        )
        result = await db.execute(stmt)
        await db.commit()
        inserted = result.rowcount or 0

        added += inserted
        avoid_sample = list(existing)
        logger.info(
            "%s: +%d this batch (attempt %d), total %d/%d",
            level.value, inserted, attempts, have + added, target,
        )

    return {"level": level.value, "before": have, "added": added, "after": have + added, "target": target}


async def run(*, apply: bool, only_level: str | None) -> int:
    levels = [LanguageLevel(only_level)] if only_level else list(TARGET_PER_LEVEL.keys())
    summary = []
    async with AsyncSessionLocal() as db:
        for level in levels:
            result = await seed_level(db, level, target=TARGET_PER_LEVEL[level], apply=apply)
            summary.append(result)

    print("\n=== Word bank seed summary ===")
    for r in summary:
        print(f"  {r['level']}: {r['before']} -> {r['after']} (target {r['target']}, +{r['added']})")
    if not apply:
        print("\nDRY RUN — no rows written. Re-run with --apply to persist.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the fixed per-level vocabulary word bank")
    parser.add_argument("--apply", action="store_true", help="Actually write rows (default: dry run)")
    parser.add_argument("--level", choices=[lvl.value for lvl in LanguageLevel], help="Only seed this level")
    args = parser.parse_args()
    return asyncio.run(run(apply=args.apply, only_level=args.level))


if __name__ == "__main__":
    raise SystemExit(main())
