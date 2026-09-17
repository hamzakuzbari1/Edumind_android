"""Adaptive, self-replenishing reading practice.

Serves one reading passage at a time at the student's current reading level (adaptive — the level
is nudged up/down by performance in submit_reading), generating fresh AI content on demand when the
bank runs low so the supply is effectively infinite.
"""

from __future__ import annotations

import json
import logging
import re

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.content import LanguageContentItem
from app.models.language.engagement import LanguageActivityLog
from app.models.language.enums import LanguageContentProgressStatus, LanguageLevel, LanguageSkill
from app.models.language.profile import LanguageStudentProfile
from app.models.language.progress import LanguageReadingProgress
from app.services.ai_service import generate_llm_json
from app.services.language_cache import TTLCache
from app.services.language_conversation_prompts import level_calibration_line
from app.services.language_generation_gate import (
    can_generate,
    note_failure as note_generation_failure,
    note_success as note_generation_success,
)
from app.services.language_content_service import get_reading_lesson, lesson_body_for_student
from app.services.language_lesson_generation_service import generate_and_store
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR
from app.services.language_subscription_service import get_default_language

logger = logging.getLogger(__name__)

_ON_DEMAND_BATCH = 3

# Curated reading interests the learner can opt into (drives generated-passage topics).
READING_TOPIC_OPTIONS = [
    "Daily life", "Work & jobs", "Travel", "Food & cooking", "Health", "Sport",
    "Science", "Technology", "Environment", "Culture & traditions",
    "News & current events", "History", "Money & shopping", "Education",
]
_MAX_TOPICS = 5

_SUMMARY_SYSTEM = (
    "You are an English reading-comprehension examiner for German learners. Judge whether the "
    "student's summary captures the passage's main ideas — reward understanding, not length or "
    "perfect grammar. Be encouraging but honest. English only. Return ONLY valid JSON."
)


def _parse_json_object(raw: str) -> dict | None:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        data = json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


_EXPLAIN_SYSTEM = (
    "You are a friendly English teacher for German learners. Explain a sentence simply and briefly "
    "at the learner's level: what it means, and one note on its grammar/structure. English only. "
    "Return ONLY valid JSON."
)

# Whole-passage glossary is stable per content item — cache so tapping any word is instant.
_GLOSSARY_CACHE = TTLCache()
_GLOSSARY_TTL = 7 * 24 * 3600  # 7 days


async def reading_glossary(db: AsyncSession, *, student_id: int, content_id: int) -> dict:
    """Pre-compute a definition for every potentially-hard word in a passage in ONE call, so tapping
    any word is instant. Cached per content item. Returns {"glossary": {word_lower: {...}}}."""
    cached = _GLOSSARY_CACHE.get(content_id)
    if cached is not None:
        return {"glossary": cached}

    item, _ = await get_reading_lesson(db, student_id=student_id, content_id=content_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    passage = ((item.body_json or {}).get("passage") or "").strip()
    if not passage:
        return {"glossary": {}}

    # Build from the offline WordNet dictionary — free, instant, no quota. Covers the passage's
    # content words; tapping any of them is then instant even when Gemini is unavailable.
    from app.services.language_dictionary_service import lookup as dict_lookup

    glossary: dict[str, dict] = {}
    seen: set[str] = set()
    for raw_word in re.findall(r"[A-Za-z][A-Za-z'-]+", passage):
        key = raw_word.lower()
        if len(key) < 4 or key in seen:  # skip short/function-ish words + duplicates
            continue
        seen.add(key)
        entries = dict_lookup(raw_word, max_entries=1)
        if not entries:
            continue
        definition = (entries[0].get("definition") or "").strip()
        if not definition:
            continue
        glossary[key] = {
            "word": raw_word,
            "part_of_speech": str(entries[0].get("part_of_speech") or "").strip(),
            "definition": definition,
            "cefr_level": "",
        }
        if len(glossary) >= 60:
            break

    if glossary:
        _GLOSSARY_CACHE.set(content_id, glossary, _GLOSSARY_TTL)
    return {"glossary": glossary}


async def explain_sentence(*, sentence: str, level: str = "A2") -> dict:
    """On-demand AI explanation of a single sentence (meaning + a grammar note). Never raises."""
    sentence = (sentence or "").strip()
    if not sentence:
        return {"explanation": ""}
    prompt = (
        f'Explain this English sentence for a {level} learner: "{sentence}".'
        + level_calibration_line(level) + "\n"
        'Return ONLY JSON: {"meaning": short plain-English paraphrase, '
        '"grammar_note": one short note about the structure/grammar}.'
    )
    try:
        raw = await generate_llm_json(prompt, system=_EXPLAIN_SYSTEM, temperature=0.3, max_output_tokens=400)
        data = _parse_json_object(raw)
        if data:
            meaning = str(data.get("meaning") or "").strip()
            note = str(data.get("grammar_note") or "").strip()
            explanation = meaning + (f"\n\nGrammar: {note}" if note else "")
            return {"explanation": explanation.strip()}
    except Exception as exc:  # pragma: no cover - LLM variance
        logger.warning("explain_sentence failed: %s", exc)
    return {"explanation": "Explanation is temporarily unavailable. Please try again."}


async def grade_summary(db: AsyncSession, *, student_id: int, content_id: int, summary: str) -> dict:
    """Grade a student's free-text summary of a passage for comprehension (AI), feed the model."""
    item, _progress = await get_reading_lesson(db, student_id=student_id, content_id=content_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    passage = ((item.body_json or {}).get("passage") or "").strip()
    summary = (summary or "").strip()
    if not passage or len(summary) < 3:
        return {"score_percent": 0.0, "feedback": "Write a short summary first.", "covered_points": [], "missed_points": []}

    level = item.level.value if item.level else "A2"
    prompt = (
        f"PASSAGE (level {level}):\n{passage}\n\n"
        f"STUDENT SUMMARY:\n{summary}\n\n"
        "Assess how well the summary captures the passage's main ideas. Return ONLY JSON with EXACTLY: "
        "score_percent (0-100 integer for comprehension), "
        "feedback (1-2 encouraging English sentences), "
        "covered_points (list of main ideas the student GOT), "
        "missed_points (list of important ideas the student MISSED)."
    )
    score = 0.0
    result = {"score_percent": 0.0, "feedback": "", "covered_points": [], "missed_points": []}
    try:
        raw = await generate_llm_json(prompt, system=_SUMMARY_SYSTEM, temperature=0.3, max_output_tokens=700)
        data = _parse_json_object(raw)
        if data:
            score = max(0.0, min(100.0, float(data.get("score_percent") or 0)))
            result = {
                "score_percent": score,
                "feedback": str(data.get("feedback") or ""),
                "covered_points": [str(p) for p in (data.get("covered_points") or [])][:6],
                "missed_points": [str(p) for p in (data.get("missed_points") or [])][:6],
            }
    except Exception as exc:  # pragma: no cover - LLM variance
        logger.warning("Summary grading failed (content=%s): %s", content_id, exc)
        return {"score_percent": 0.0, "feedback": "The summary check is temporarily unavailable. Please try again.", "covered_points": [], "missed_points": []}

    # Feed the learner model: summarizing is reading comprehension at the passage's level.
    try:
        from app.services.language_learner_events import record_scored_practice

        language = await get_default_language(db)
        await record_scored_practice(
            db, student_id=student_id, language_id=language.id, skill=LanguageSkill.reading,
            level=item.level, score_percent=score, source="reading",
        )
    except Exception:  # never let evidence recording break the response
        pass
    return result


def nudge_reading_level(current: LanguageLevel | None, score_percent: float) -> LanguageLevel:
    """Adaptive step: strong pass -> harder, weak attempt -> easier, else stay (clamped A1..C2)."""
    # CEFR_RANK is 1..6 (A1..C2); clamp within that range — NOT 0..5, which crashed on RANK_CEFR[0]
    # for an A1 learner scoring < 40 and could never reach C2.
    rank = CEFR_RANK.get(current, 1) if current else 1
    if score_percent >= 85:
        rank = min(rank + 1, 6)
    elif score_percent < 40:
        rank = max(rank - 1, 1)
    return RANK_CEFR[rank]


async def _adaptive_level(db: AsyncSession, *, student_id: int, language_id: int) -> str:
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics and analytics.reading_level:
        return analytics.reading_level.value
    return "A2"


async def _unseen_reading(
    db: AsyncSession, *, student_id: int, language_id: int, level: str, generated_only: bool = False,
    length: str = "", newest: bool = False,
) -> LanguageContentItem | None:
    seen = select(LanguageReadingProgress.content_item_id).where(
        LanguageReadingProgress.student_id == student_id,
        LanguageReadingProgress.status == LanguageContentProgressStatus.completed,
    )
    q = select(LanguageContentItem).where(
        LanguageContentItem.language_id == language_id,
        LanguageContentItem.skill == LanguageSkill.reading,
        LanguageContentItem.content_type == "lesson",
        LanguageContentItem.level == LanguageLevel(level),
        LanguageContentItem.is_published.is_(True),
        LanguageContentItem.id.notin_(seen),
    )
    if generated_only:
        # AI-generated items carry source='ai_nightly' and the rich explanation/quote/type fields.
        q = q.where(LanguageContentItem.body_json["source"].astext == "ai_nightly")
    # Serve the requested length: short/long must match exactly; medium also matches untagged items.
    rl = LanguageContentItem.body_json["reading_length"].astext
    if length == "short":
        q = q.where(rl == "short")
    elif length == "long":
        q = q.where(rl == "long")
    elif length == "medium":
        q = q.where(or_(rl == "medium", rl.is_(None)))
    # newest=True serves the just-generated passage (id desc); otherwise a random unseen one.
    q = q.order_by(LanguageContentItem.id.desc() if newest else func.random()).limit(1)
    return (await db.execute(q)).scalar_one_or_none()


async def _profile(db: AsyncSession, *, student_id: int, language_id: int) -> LanguageStudentProfile | None:
    return (
        await db.execute(
            select(LanguageStudentProfile).where(
                LanguageStudentProfile.student_id == student_id,
                LanguageStudentProfile.language_id == language_id,
            )
        )
    ).scalar_one_or_none()


async def get_reading_topics(db: AsyncSession, *, student_id: int) -> dict:
    """The curated topic options + the topics this learner has opted into."""
    language = await get_default_language(db)
    profile = await _profile(db, student_id=student_id, language_id=language.id)
    selected = list(((profile.preferences_json or {}) if profile else {}).get("reading_topics") or [])
    return {"options": READING_TOPIC_OPTIONS, "selected": selected}


async def set_reading_topics(db: AsyncSession, *, student_id: int, topics: list[str]) -> dict:
    """Persist the learner's reading interests (validated against the curated list, capped)."""
    language = await get_default_language(db)
    valid_lower = {t.lower(): t for t in READING_TOPIC_OPTIONS}
    selected: list[str] = []
    for t in topics or []:
        canon = valid_lower.get((t or "").strip().lower())
        if canon and canon not in selected:
            selected.append(canon)
        if len(selected) >= _MAX_TOPICS:
            break
    profile = await _profile(db, student_id=student_id, language_id=language.id)
    if profile is not None:
        prefs = dict(profile.preferences_json or {})
        prefs["reading_topics"] = selected
        profile.preferences_json = prefs  # reassign so SQLAlchemy tracks the JSONB change
    return {"options": READING_TOPIC_OPTIONS, "selected": selected}


async def reading_history(db: AsyncSession, *, student_id: int, limit: int = 30) -> list[dict]:
    """Passages the learner has completed — their reading library, newest first."""
    rows = (
        await db.execute(
            select(LanguageContentItem, LanguageReadingProgress)
            .join(LanguageReadingProgress, LanguageReadingProgress.content_item_id == LanguageContentItem.id)
            .where(
                LanguageReadingProgress.student_id == student_id,
                LanguageReadingProgress.status == LanguageContentProgressStatus.completed,
            )
            .order_by(LanguageReadingProgress.completed_at.desc().nullslast())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": item.id,
            "title": item.title,
            "level": item.level.value if item.level else None,
            "topic": (item.body_json or {}).get("topic") or item.title,
            "score_percent": prog.score_percent,
            "completed_at": prog.completed_at,
        }
        for item, prog in rows
    ]


async def reading_insights(db: AsyncSession, *, student_id: int) -> dict:
    """Reading analytics for the learner: WPM trend, comprehension, and per-skill strengths/gaps."""
    language = await get_default_language(db)
    rows = (
        await db.execute(
            select(LanguageActivityLog.payload_json, LanguageActivityLog.created_at)
            .where(
                LanguageActivityLog.student_id == student_id,
                LanguageActivityLog.language_id == language.id,
                LanguageActivityLog.event_type == "reading_lesson_completed",
            )
            .order_by(LanguageActivityLog.created_at.desc())
            .limit(20)
        )
    ).all()
    wpms: list[int] = []
    scores: list[float] = []
    for payload, _created in rows:
        p = payload or {}
        if isinstance(p.get("wpm"), (int, float)) and p["wpm"]:
            wpms.append(int(p["wpm"]))
        if isinstance(p.get("score_percent"), (int, float)):
            scores.append(float(p["score_percent"]))
    wpms.reverse()  # chronological for a trend line

    from app.services.language_learner_model_service import LanguageLearnerModelService

    profile = await LanguageLearnerModelService(db).get_component_profile(
        student_id=student_id, language_id=language.id
    )
    reading_comps = [c for c in profile if c.get("skill") == "reading"]

    def _skill(c: dict) -> dict:
        return {"code": c["code"], "mastery": round((c.get("p_mastery") or 0.0) * 100)}

    weak = [_skill(c) for c in sorted(reading_comps, key=lambda c: c.get("p_mastery") or 0.0)[:3]]
    strong = [_skill(c) for c in sorted(reading_comps, key=lambda c: -(c.get("p_mastery") or 0.0))[:3]]
    return {
        "wpm_recent": wpms[-10:],
        "avg_wpm": round(sum(wpms) / len(wpms)) if wpms else None,
        "best_wpm": max(wpms) if wpms else None,
        "avg_comprehension": round(sum(scores) / len(scores), 1) if scores else None,
        "lessons_completed": len(rows),
        "weak_skills": weak,
        "strong_skills": strong,
    }


async def next_reading(db: AsyncSession, *, student_id: int, length: str = "") -> dict | None:
    """The next adaptive reading passage (stripped of answers), generating content if the bank is low.

    ``length`` (short|medium|long) lets the learner pick how long the generated passage is.
    """
    language = await get_default_language(db)
    level = await _adaptive_level(db, student_id=student_id, language_id=language.id)

    # Token-saving: serve an existing unseen AI passage first (free, instant). Generate ONLY when the
    # fresh-AI pool is exhausted — and even then, skip while the breaker is tripped (e.g. Gemini
    # credits depleted) so we don't waste calls. The seeded bank is the always-available fallback.
    item = await _unseen_reading(
        db, student_id=student_id, language_id=language.id, level=level, generated_only=True, length=length
    )
    if item is None and can_generate():
        profile = await _profile(db, student_id=student_id, language_id=language.id)
        topics = ", ".join(((profile.preferences_json or {}) if profile else {}).get("reading_topics") or [])
        from app.services.language_adaptive_generation_service import build_adaptive_context

        adaptive_context = await build_adaptive_context(
            db, student_id=student_id, language_id=language.id, skill="reading"
        )
        try:
            made = await generate_and_store(
                db, language_id=language.id, skill="reading", level=level, count=_ON_DEMAND_BATCH,
                topics=topics, length=length, adaptive_context=adaptive_context,
            )
            if made:
                note_generation_success()
                await db.commit()  # persist generated passages (GET endpoint won't commit otherwise)
                item = await _unseen_reading(
                    db, student_id=student_id, language_id=language.id, level=level,
                    generated_only=True, length=length, newest=True,
                )
            else:
                note_generation_failure()  # nothing produced (quota/credits) — back off
        except Exception as exc:  # pragma: no cover - LLM variance
            logger.warning("On-demand reading generation failed (%s): %s", level, exc)
            note_generation_failure()
            await db.rollback()

    # Fallbacks: any unseen AI passage (ignore length), then the seeded bank (always works offline).
    if item is None:
        item = await _unseen_reading(db, student_id=student_id, language_id=language.id, level=level, generated_only=True)
    if item is None:
        item = await _unseen_reading(db, student_id=student_id, language_id=language.id, level=level)
    if item is None:
        return None

    body = lesson_body_for_student(item)
    return {
        "id": item.id,
        "title": item.title,
        "level": item.level.value if item.level else level,
        "topic": (item.body_json or {}).get("topic") or item.title,
        "passage": body.get("passage") or "",
        "glossary": body.get("glossary") or [],
        "questions": body.get("questions") or [],
    }
