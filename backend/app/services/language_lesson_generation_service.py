"""Nightly AI lesson generation — keep each (skill, level) lesson pool topped up.

A cron/off-peak job calls run_nightly_topup(); Claude generates fresh, CEFR-aligned lessons
(woven with the level's curriculum grammar/vocab themes), they are validated with the same
rules as the seed content, then stored as published LanguageContentItem rows. During the day
the normal lesson endpoints serve them from the (now larger, fresher) pool — no live AI cost.

Falls back to a no-op when Claude is unavailable, so the seeded 240 always remain.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.services.ai_service import generate_llm_json
from app.services.claude_service import is_claude_configured
from app.services.language_curriculum_service import get_level_curriculum
from app.services.language_subscription_service import get_default_language

logger = logging.getLogger(__name__)
settings = get_settings()

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
SKILLS = ["reading", "listening", "writing", "speaking"]
CONTENT_TYPE = {
    "reading": "lesson",
    "listening": "lesson",
    "writing": "writing_prompt",
    "speaking": "speaking_prompt",
}
# Keep at least this many published lessons available per (skill, level); generate the deficit.
TARGET_PER_BUCKET = 12
# Generate at most this many per call (keeps each LLM response small enough to not truncate).
MAX_PER_CALL = 3
# Rough passage length per CEFR level (reading/listening).
WORDS_FOR_LEVEL = {"A1": 45, "A2": 70, "B1": 110, "B2": 170, "C1": 230, "C2": 280}
# Optional learner-chosen reading length, applied as a multiplier on the level's base word count.
LENGTH_MULTIPLIER = {"short": 0.6, "medium": 1.0, "long": 1.6}


def _parse(raw: str) -> list[dict] | None:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        data = json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return None
    items = data.get("items")
    return items if isinstance(items, list) and items else None


def _valid_mcq(body: dict, *, expected_count: int | None = None) -> bool:
    qs = body.get("questions")
    if not isinstance(qs, list) or not qs:
        return False
    if expected_count is not None and len(qs) != expected_count:
        return False
    for q in qs:
        ch = q.get("choices")
        # 2-4 options: 4 for standard MCQ, 3 for True/False/Not Given, 2 for True/False.
        if not isinstance(ch, list) or not (2 <= len(ch) <= 4):
            return False
        ci = q.get("correct_index")
        if not isinstance(ci, int) or not (0 <= ci < len(ch)):
            return False
    return True


def _build_prompt(skill: str, level: str, count: int, themes: str, topics: str = "", length: str = "", adaptive_context: str = "") -> tuple[str, str]:
    from app.services.language_conversation_prompts import level_guidance

    words = WORDS_FOR_LEVEL.get(level, 100)
    if skill == "reading" and length in LENGTH_MULTIPLIER:
        words = max(25, round(words * LENGTH_MULTIPLIER[length]))
    theme_line = f" Reinforce these grammar/vocabulary themes where natural: {themes}." if themes else ""
    topic_line = f" Prefer topics the learner enjoys: {topics}." if topics else ""
    # Calibrate the ACTUAL difficulty to the CEFR level — vocabulary range, grammar complexity and
    # topic difficulty — so a B2 passage is genuinely harder than an A2 one (not just labelled).
    level_line = (
        f" Calibrate the difficulty precisely to CEFR {level} (apply the vocabulary, grammar and topic "
        f"complexity below; ignore any 'reply shape' note): {level_guidance(level)}"
    )
    common = (
        f"You are a CEFR curriculum author. Generate exactly {count} DISTINCT CEFR {level} "
        f"English {skill} lessons for Syrian learners (everyday/school-life topics)."
        f"{theme_line}{topic_line} ENGLISH ONLY — every field must be written in English (no Arabic)."
        + level_line
    )
    if skill == "reading":
        # English-only, richer comprehension items: 5 mixed-type questions, each with a teaching
        # explanation and an exact supporting quote from the passage (for the UI to highlight).
        sys = (
            f"You are a CEFR curriculum author writing IELTS-style reading tasks. Generate exactly {count} "
            f"DISTINCT CEFR {level} English reading lessons for learners (everyday/integration topics)."
            f"{theme_line}{topic_line}{level_line} ENGLISH ONLY. "
            f"Each lesson: a ~{words}-word English passage + exactly 5 questions covering a MIX of these "
            "IELTS-style types:\n"
            "- main_idea / detail / inference / vocab_in_context: 4 choices, exactly one correct.\n"
            '- true_false_notgiven: a statement; choices MUST be EXACTLY ["True","False","Not Given"] '
            "(correct_index 0/1/2). Use 'Not Given' when the passage neither confirms nor contradicts it.\n"
            "- sentence_completion: a sentence summarising part of the passage with ONE blank shown as "
            "'_____'; 4 word/phrase options, exactly one correct.\n"
            "- heading_match: 'Which heading best fits the paragraph starting \"<first few words>\"?' with "
            "4 short heading options, exactly one correct.\n"
            "Include at least 2 of {true_false_notgiven, sentence_completion, heading_match} per lesson. "
            "For each question include a short English explanation, and evidence_quote = an EXACT substring "
            "copied from the passage that supports the answer (use \"\" for true_false_notgiven = Not Given). "
            "Also include glossary = 3-5 KEY words from the passage a learner at this level may not know, "
            "each with a short English definition (to pre-teach before reading). "
            'Return ONLY JSON: {"items":[{"title": str, "topic": str, "passage": str, '
            '"glossary":[{"word": str, "definition": str}], "questions":['
            '{"stem": str, "choices":[2-4 strings], "correct_index": int, '
            '"type": "main_idea|detail|inference|vocab_in_context|true_false_notgiven|sentence_completion|heading_match", '
            '"explanation": str, "evidence_quote": str}]}]}'
        )
    elif skill == "listening":
        # English-only output, mirroring the reading generator.
        sys = (
            f"You are a CEFR curriculum author writing IELTS-style listening tasks. Generate exactly {count} "
            f"DISTINCT CEFR {level} English listening lessons for learners (everyday/integration topics)."
            f"{theme_line}{topic_line}{level_line} ENGLISH ONLY. "
            f"Each lesson: a ~{words}-word English audio_transcript (natural spoken English — a talk, "
            "dialogue or announcement) + exactly 4 questions covering a MIX of IELTS-style listening types:\n"
            "- main_idea / detail / inference: 4 choices, exactly one correct.\n"
            '- true_false_notgiven: choices MUST be EXACTLY ["True","False","Not Given"].\n'
            "- sentence_completion: a sentence about what was said with ONE blank '_____' + 4 options.\n"
            "Include at least 1 of {true_false_notgiven, sentence_completion}. For each question add a short "
            "English explanation, and evidence_quote = an EXACT substring from the transcript ('' for Not Given). "
            "Use the adaptive context to choose the student's level, purpose, and scenario. Avoid repeating stock "
            "airport gate announcements, hotel bookings, or travel delays unless the adaptive context explicitly "
            "makes that the best fit. "
            'Return ONLY JSON: {"items":[{"title": str, "audio_transcript": str, '
            '"instructions": short English listening instruction, '
            '"questions":[{"stem": str, "choices":[2-4 strings], "correct_index": int, '
            '"type": "main_idea|detail|inference|true_false_notgiven|sentence_completion", '
            '"explanation": str, "evidence_quote": str}]}]}'
        )
    elif skill == "writing":
        sys = (
            common
            + " Each lesson: a clear writing prompt + a minimum word count appropriate to the level. "
            'Return ONLY JSON: {"items":[{"title": str, "prompt": str, '
            '"min_words": int, "min_sentences": int}]}'
        )
    else:  # speaking
        sys = (
            common
            + " Each lesson: a speaking prompt the learner answers aloud + a minimum duration in seconds. "
            'Return ONLY JSON: {"items":[{"title": str, "prompt": str, "min_seconds": int}]}'
        )
    # Phase 7 — prepend the learner's adaptive context (interests/weaknesses/effective level) BEFORE
    # the existing prompt, never replacing it (Prompt Enrichment Pattern). Empty = unchanged.
    if adaptive_context and adaptive_context.strip():
        sys = f"{adaptive_context.strip()}\n\n{sys}"
    user = f"Write the {count} CEFR {level} {skill} lessons now as JSON."
    return sys, user


def _to_body(skill: str, level: str, raw: dict) -> dict | None:
    """Normalize a raw generated item into a stored body_json; return None if invalid."""
    title = str(raw.get("title") or "").strip()
    if not title:
        return None
    # English-only: every stored field is English. The legacy *_ar keys are kept
    # for backward-compatible readers but now MIRROR the English text (never Arabic).
    title_ar = title
    body: dict = {"title_ar": title_ar, "source": "ai_nightly", "generated_at": datetime.now(timezone.utc).isoformat()}
    if skill == "reading":
        passage = str(raw.get("passage") or "").strip()
        if not passage:
            return None
        questions = []
        for i, q in enumerate(raw.get("questions") or [], start=1):
            if not isinstance(q, dict):
                continue
            questions.append({
                "id": q.get("id") or f"q{i}",
                "stem": str(q.get("stem") or "").strip(),
                "choices": q.get("choices") or [],
                "correct_index": q.get("correct_index"),
                "type": str(q.get("type") or "detail").strip(),
                "explanation": str(q.get("explanation") or "").strip(),
                "evidence_quote": str(q.get("evidence_quote") or "").strip(),
            })
        glossary = []
        for g in (raw.get("glossary") or [])[:6]:
            if isinstance(g, dict) and (g.get("word") or "").strip():
                glossary.append({
                    "word": str(g.get("word") or "").strip(),
                    "definition": str(g.get("definition") or "").strip(),
                })
        body.update(
            topic=str(raw.get("topic") or title).strip(),
            passage=passage,
            glossary=glossary,
            questions=questions,
        )
        if not _valid_mcq(body):
            return None
    elif skill == "listening":
        transcript = str(raw.get("audio_transcript") or "").strip()
        if not transcript:
            return None
        questions = []
        for i, q in enumerate(raw.get("questions") or [], start=1):
            if not isinstance(q, dict):
                continue
            questions.append({
                "id": q.get("id") or f"q{i}",
                "stem": str(q.get("stem") or "").strip(),
                "choices": q.get("choices") or [],
                "correct_index": q.get("correct_index"),
                "type": str(q.get("type") or "detail").strip(),
                "explanation": str(q.get("explanation") or "").strip(),
                "evidence_quote": str(q.get("evidence_quote") or "").strip(),
            })
        body.update(
            audio_transcript=transcript,
            instructions=str(raw.get("instructions") or "Listen and answer the questions.").strip(),
            questions=questions,
        )
        if not _valid_mcq(body, expected_count=4):
            return None
    elif skill == "writing":
        prompt = str(raw.get("prompt") or "").strip()
        if not prompt or not isinstance(raw.get("min_words"), int):
            return None
        body.update(
            prompt=prompt,
            prompt_ar=prompt,  # English-only: mirror the English prompt (legacy *_ar key)
            min_words=int(raw["min_words"]),
            min_sentences=int(raw.get("min_sentences") or 2),
        )
    else:  # speaking
        prompt = str(raw.get("prompt") or "").strip()
        if not prompt or not isinstance(raw.get("min_seconds"), int):
            return None
        body.update(
            prompt=prompt,
            prompt_ar=prompt,  # English-only: mirror the English prompt (legacy *_ar key)
            min_seconds=int(raw["min_seconds"]),
        )
    return {"title": title, "body": body}


async def _existing_titles(
    db: AsyncSession, *, language_id: int, skill: str, level: str, student_id: int | None = None
) -> set[str]:
    _ = student_id
    query = select(LanguageContentItem.title).where(
        LanguageContentItem.language_id == language_id,
        LanguageContentItem.skill == LanguageSkill(skill),
        LanguageContentItem.level == LanguageLevel(level),
        LanguageContentItem.content_type == CONTENT_TYPE[skill],
    )
    rows = await db.execute(query)
    return {str(t).strip() for (t,) in rows.all() if t}


async def _published_count(db: AsyncSession, *, language_id: int, skill: str, level: str) -> int:
    res = await db.execute(
        select(func.count())
        .select_from(LanguageContentItem)
        .where(
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.skill == LanguageSkill(skill),
            LanguageContentItem.level == LanguageLevel(level),
            LanguageContentItem.content_type == CONTENT_TYPE[skill],
            LanguageContentItem.is_published.is_(True),
        )
    )
    return int(res.scalar() or 0)


async def generate_and_store(
    db: AsyncSession, *, language_id: int, skill: str, level: str, count: int, topics: str = "",
    length: str = "", adaptive_context: str = "", student_id: int | None = None,
    source: str | None = None, body_extras: dict | None = None,
) -> int:
    """Generate up to `count` lessons for (skill, level) and store the valid, non-duplicate ones.

    ``topics`` (optional) nudges the generator toward subjects the learner enjoys (personalization).
    ``length`` (optional, reading) — short|medium|long passage length.
    ``adaptive_context`` (optional) — a [ADAPTIVE CONTEXT] block (Phase 7) targeting the learner's
    effective level / weaknesses / interests; prepended to the prompt.
    """
    if not is_claude_configured() or count <= 0:
        return 0
    objectives = await get_level_curriculum(level)
    themes = ", ".join(
        f"{o.get('grammar') or ''} / {o.get('vocab') or ''}".strip(" /") for o in objectives[:5]
    )
    existing = await _existing_titles(
        db, language_id=language_id, skill=skill, level=level, student_id=student_id
    )
    inserted = 0
    remaining = count
    while remaining > 0:
        n = min(MAX_PER_CALL, remaining)
        sys, user = _build_prompt(skill, level, n, themes, topics, length, adaptive_context)
        try:
            raw = await generate_llm_json(user, system=sys, temperature=0.7, max_output_tokens=8192)
        except Exception as exc:
            logger.warning("lesson gen failed [%s][%s]: %s", skill, level, exc)
            break
        items = _parse(raw)
        if not items:
            break
        produced = 0
        for raw_item in items:
            norm = _to_body(skill, level, raw_item if isinstance(raw_item, dict) else {})
            if not norm or norm["title"] in existing:
                continue
            if source:
                norm["body"]["source"] = source
            if body_extras:
                norm["body"].update(body_extras)
            if skill == "reading":
                # Tag the passage's length so the reader can be served the length it asked for.
                norm["body"]["reading_length"] = length if length in LENGTH_MULTIPLIER else "medium"
            existing.add(norm["title"])
            db.add(
                LanguageContentItem(
                    language_id=language_id,
                    skill=LanguageSkill(skill),
                    level=LanguageLevel(level),
                    content_type=CONTENT_TYPE[skill],
                    title=norm["title"],
                    body_json=norm["body"],
                    student_id=student_id,
                    sort_order=0,
                    is_published=True,
                )
            )
            inserted += 1
            produced += 1
        await db.flush()
        remaining -= n
        if produced == 0:  # model returned nothing usable — stop hammering quota
            break
    return inserted


async def run_nightly_topup(
    db: AsyncSession, *, language_id: int | None = None, target: int = TARGET_PER_BUCKET
) -> dict:
    """Top every (skill, level) bucket up to `target` published lessons. Returns a summary."""
    if language_id is None:
        language = await get_default_language(db)
        language_id = language.id
    summary: dict[str, int] = {}
    total = 0
    for skill in SKILLS:
        for level in LEVELS:
            have = await _published_count(db, language_id=language_id, skill=skill, level=level)
            deficit = max(0, target - have)
            if deficit <= 0:
                continue
            made = await generate_and_store(db, language_id=language_id, skill=skill, level=level, count=deficit)
            if made:
                summary[f"{skill}_{level}"] = made
                total += made
    summary["_total"] = total
    return summary
