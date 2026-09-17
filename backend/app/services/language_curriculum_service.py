"""Auto-built, CEFR-aligned curriculum per level — mapped to our own features.

Each level has a set of learning objectives (CEFR can-do statements) with a grammar
focus, a vocabulary theme, an example, and the platform feature that best practices it
(conversation / shadowing / pronunciation / reading / listening / writing / vocabulary).

The curriculum is generated automatically by the LLM (cached per level) and always falls
back to a curated, CEFR-aligned skeleton so it is reliable and "studied" even with no AI.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.language.analytics import LanguageAnalytics
from app.models.language.enums import LanguageLevel
from app.models.language.progress import LanguageCurriculumProgress
from app.services.ai_service import generate_llm_json
from app.services.claude_service import is_claude_configured
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR, bottleneck_level
from app.services.language_subscription_service import get_default_language

PRACTICE_TO_MASTER = 3

logger = logging.getLogger(__name__)
settings = get_settings()

FEATURES = ["conversation", "shadowing", "pronunciation", "reading", "listening", "writing", "vocabulary"]
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Curated CEFR skeleton — the reliable, well-studied base (and the AI fallback).
_CURATED: dict[str, list[dict]] = {
    "A1": [
        {"title": "Introduce yourself", "grammar": "verb 'to be', personal pronouns", "vocab": "names, countries, jobs", "example": "My name is Sara. I am from Syria.", "feature": "conversation"},
        {"title": "Talk about family & people", "grammar": "possessives, have/has", "vocab": "family members", "example": "This is my brother. He has two children.", "feature": "conversation"},
        {"title": "Describe your daily routine", "grammar": "present simple", "vocab": "daily activities, time", "example": "I get up at seven and go to work.", "feature": "shadowing"},
        {"title": "Numbers, sounds & greetings", "grammar": "basic questions", "vocab": "numbers, greetings", "example": "How are you? I am fine, thank you.", "feature": "pronunciation"},
        {"title": "Order food and shop", "grammar": "this/that, a/an", "vocab": "food, prices", "example": "I would like a coffee, please.", "feature": "conversation"},
    ],
    "A2": [
        {"title": "Talk about the past", "grammar": "past simple", "vocab": "time expressions", "example": "Yesterday I visited my friend.", "feature": "conversation"},
        {"title": "Make future plans", "grammar": "going to / will", "vocab": "leisure, weekend", "example": "I am going to travel next week.", "feature": "conversation"},
        {"title": "Describe places", "grammar": "there is / there are, prepositions", "vocab": "town, directions", "example": "There is a park near my house.", "feature": "reading"},
        {"title": "Compare things", "grammar": "comparatives", "vocab": "adjectives", "example": "This book is cheaper than that one.", "feature": "writing"},
        {"title": "Linking & connected speech", "grammar": "—", "vocab": "common phrases", "example": "What do you want to do?", "feature": "shadowing"},
    ],
    "B1": [
        {"title": "Express and justify opinions", "grammar": "because / so / although", "vocab": "opinion phrases", "example": "I think reading is useful because it builds vocabulary.", "feature": "conversation"},
        {"title": "Narrate experiences", "grammar": "present perfect vs past simple", "vocab": "travel, experiences", "example": "I have been to Italy twice.", "feature": "conversation"},
        {"title": "Talk about hypotheticals", "grammar": "first & second conditional", "vocab": "decisions", "example": "If I had time, I would study more.", "feature": "conversation"},
        {"title": "Word stress & intonation", "grammar": "—", "vocab": "multi-syllable words", "example": "I would really appreciate your help.", "feature": "pronunciation"},
        {"title": "Write a short structured text", "grammar": "connectors", "vocab": "linking words", "example": "First, ... Then, ... Finally, ...", "feature": "writing"},
    ],
    "B2": [
        {"title": "Argue a point of view", "grammar": "complex clauses", "vocab": "debate, persuasion", "example": "Although it is expensive, the benefits outweigh the cost.", "feature": "conversation"},
        {"title": "Discuss news & abstract ideas", "grammar": "passive, reported speech", "vocab": "current affairs", "example": "It was reported that prices had risen.", "feature": "reading"},
        {"title": "Use idioms & collocations", "grammar": "collocation patterns", "vocab": "idioms", "example": "Let's get to the point.", "feature": "vocabulary"},
        {"title": "Fluency, rhythm & weak forms", "grammar": "—", "vocab": "natural phrasing", "example": "I'd have done it differently.", "feature": "pronunciation"},
        {"title": "Write a cohesive essay", "grammar": "cohesion, referencing", "vocab": "academic linkers", "example": "Moreover, this suggests that ...", "feature": "writing"},
    ],
    "C1": [
        {"title": "Discuss with nuance", "grammar": "hedging, discourse markers", "vocab": "precise verbs", "example": "It could be argued that ...", "feature": "conversation"},
        {"title": "Use professional register", "grammar": "formal structures", "vocab": "professional terms", "example": "I would like to address several concerns.", "feature": "writing"},
        {"title": "Refine prosody & emphasis", "grammar": "—", "vocab": "stress for meaning", "example": "I never SAID she took it.", "feature": "pronunciation"},
        {"title": "Infer meaning in texts & talks", "grammar": "inference", "vocab": "implicit meaning", "example": "Reading between the lines, ...", "feature": "listening"},
        {"title": "Write persuasively", "grammar": "rhetorical devices", "vocab": "persuasive language", "example": "Surely we cannot ignore this.", "feature": "writing"},
    ],
    "C2": [
        {"title": "Command master-level discourse", "grammar": "idiomatic precision", "vocab": "nuanced lexis", "example": "That is, if I may, a sweeping generalization.", "feature": "conversation"},
        {"title": "Shift register & style at will", "grammar": "stylistic control", "vocab": "tone words", "example": "From the formal to the colloquial, effortlessly.", "feature": "writing"},
        {"title": "Achieve native-like prosody", "grammar": "—", "vocab": "subtle intonation", "example": "Well, that's one way of putting it.", "feature": "pronunciation"},
        {"title": "Grasp subtle comprehension", "grammar": "nuance, irony", "vocab": "connotation", "example": "The irony was not lost on me.", "feature": "listening"},
        {"title": "Build a sophisticated argument", "grammar": "advanced rhetoric", "vocab": "abstract concepts", "example": "Notwithstanding the objections, the thesis holds.", "feature": "writing"},
    ],
}

_GEN_SYSTEM = (
    "You are a CEFR curriculum designer. For the given level, output a focused syllabus of 5 "
    "learning objectives, like an international CEFR course. Each objective must be practisable by "
    "ONE of these app features: " + ", ".join(FEATURES) + ". "
    "Return ONLY JSON: {\"objectives\": [{\"title\": can-do statement, \"grammar\": string, "
    "\"vocab\": string, \"example\": short English example, \"feature\": one of the features}]}"
)

# Cache generated curricula per level (regenerate after TTL). In-memory; swap for Redis at scale.
_CACHE_TTL = 60 * 60 * 24
_cache: dict[str, tuple[float, list[dict]]] = {}


def _curated(level: str) -> list[dict]:
    items = _CURATED.get(level, _CURATED["A1"])
    return [{"id": f"{level}-{i + 1}", "level": level, **obj} for i, obj in enumerate(items)]


def _parse(raw: str) -> list[dict] | None:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        data = json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return None
    objs = data.get("objectives")
    return objs if isinstance(objs, list) and objs else None


async def get_level_curriculum(level: str) -> list[dict]:
    """Auto-generated (cached) curriculum for a level; curated fallback on any failure."""
    level = (level or "A1").upper()
    if level not in _CURATED:
        level = "A1"

    cached = _cache.get(level)
    if cached and cached[0] > time.time():
        return cached[1]

    if is_claude_configured():
        try:
            from app.services.language_conversation_prompts import level_calibration_line

            raw = await generate_llm_json(
                f"Design the CEFR {level} curriculum now." + level_calibration_line(level),
                system=_GEN_SYSTEM,
                temperature=0.4,
                max_output_tokens=8192,
            )
            parsed = _parse(raw)
            if parsed:
                out = []
                for i, obj in enumerate(parsed[:6]):
                    feature = obj.get("feature") if obj.get("feature") in FEATURES else "conversation"
                    out.append(
                        {
                            "id": f"{level}-{i + 1}",
                            "level": level,
                            "title": str(obj.get("title") or "").strip() or "Practice objective",
                            "grammar": str(obj.get("grammar") or "").strip(),
                            "vocab": str(obj.get("vocab") or "").strip(),
                            "example": str(obj.get("example") or "").strip(),
                            "feature": feature,
                        }
                    )
                if out:
                    _cache[level] = (time.time() + _CACHE_TTL, out)
                    return out
        except Exception as exc:
            logger.warning("Curriculum AI generation failed for %s: %s", level, exc)

    curated = _curated(level)
    _cache[level] = (time.time() + _CACHE_TTL, curated)
    return curated


async def _current_level(db: AsyncSession, *, student_id: int, language_id: int) -> tuple[str, int]:
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    level: LanguageLevel | None = None
    progress = 0
    if analytics:
        level = analytics.overall_level_internal or bottleneck_level(
            {
                "reading": analytics.reading_level.value if analytics.reading_level else None,
                "listening": analytics.listening_level.value if analytics.listening_level else None,
                "writing": analytics.writing_level.value if analytics.writing_level else None,
                "speaking": analytics.speaking_level.value if analytics.speaking_level else None,
            }
        )
        conv = (analytics.skill_growth_json or {}).get("speaking", {}).get("conversation", {})
        progress = int(conv.get("mastery_progress_percent") or 0)
    return (level.value if level else "A1"), progress


async def build_curriculum_overview(db: AsyncSession, *, student_id: int) -> dict:
    language = await get_default_language(db)
    current, mastery = await _current_level(db, student_id=student_id, language_id=language.id)
    cur_rank = CEFR_RANK.get(LanguageLevel(current), 1)

    levels = []
    for lv in LEVELS:
        rank = CEFR_RANK[LanguageLevel(lv)]
        status = "done" if rank < cur_rank else ("current" if rank == cur_rank else "locked")
        levels.append({"level": lv, "status": status})

    objectives = await get_level_curriculum(current)

    # Attach each objective's tracked status (new | in_progress | mastered).
    obj_ids = [o["id"] for o in objectives]
    status_map: dict[str, str] = {}
    if obj_ids:
        res = await db.execute(
            select(LanguageCurriculumProgress.objective_id, LanguageCurriculumProgress.status).where(
                LanguageCurriculumProgress.student_id == student_id,
                LanguageCurriculumProgress.objective_id.in_(obj_ids),
            )
        )
        status_map = {oid: st for oid, st in res.all()}
    for o in objectives:
        o["status"] = status_map.get(o["id"], "new")

    mastered = sum(1 for o in objectives if o["status"] == "mastered")
    # Mastery bar = share of this level's objectives mastered (fed by BOTH the manual Practice
    # tap and real lesson results via credit_skill_objectives) — not the narrow conversation-only
    # signal. Fall back to the conversation mastery only when the level has no objectives.
    mastery_pct = int(round(100 * mastered / len(objectives))) if objectives else mastery
    next_level = RANK_CEFR.get(cur_rank + 1)
    # The level-up test unlocks only after every current-level objective is mastered.
    can_take_test = bool(next_level) and len(objectives) > 0 and mastered >= len(objectives)
    return {
        "current_level": current,
        "next_level": next_level.value if next_level else None,
        "mastery_progress_percent": mastery_pct,
        "objectives_total": len(objectives),
        "objectives_mastered": mastered,
        "can_take_test": can_take_test,
        "levels": levels,
        "objectives": objectives,
    }


async def record_objective_practice(db: AsyncSession, *, student_id: int, objective_id: str) -> dict:
    """Mark that the learner has STARTED working on an objective (status -> in_progress).

    Mastery is earned ONLY through real performance — passing real lessons or conversing — via
    `credit_skill_objectives`. A manual tap/open never masters an objective and never advances the
    mastery counter, so "X/Y mastered" reflects genuine accomplishment, not button clicks.
    """
    objective_id = (objective_id or "").strip()
    if not objective_id:
        return {"objective_id": "", "status": "new", "practice_count": 0}
    language = await get_default_language(db)
    result = await db.execute(
        select(LanguageCurriculumProgress).where(
            LanguageCurriculumProgress.student_id == student_id,
            LanguageCurriculumProgress.objective_id == objective_id,
        )
    )
    row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None:
        row = LanguageCurriculumProgress(
            student_id=student_id, language_id=language.id, objective_id=objective_id,
            status="in_progress", practice_count=0,
        )
        db.add(row)
    elif row.status == "new":
        row.status = "in_progress"  # don't downgrade a mastered objective
    row.last_practiced_at = now
    await db.flush()
    return {"objective_id": objective_id, "status": row.status, "practice_count": int(row.practice_count or 0)}


# Each skill credits mastery toward the current-level objectives tagged with these features.
SKILL_FEATURES: dict[str, set[str]] = {
    "reading": {"reading"},
    "listening": {"listening"},
    "writing": {"writing"},
    "speaking": {"conversation", "shadowing", "pronunciation"},
}


async def credit_skill_objectives(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill,
    score_percent: float,
    passed: bool,
) -> dict | None:
    """Performance path to mastery — complements the manual 'Practice' tap.

    A passed lesson advances the least-progressed current-level objective for that skill.
    A strong score (>= 85) counts double. Both paths feed the same practice_count / mastery
    counter, so real lessons and manual practice together raise the curriculum flow.
    """
    if not passed:
        return None
    sk = skill.value if hasattr(skill, "value") else str(skill)
    feats = SKILL_FEATURES.get(sk)
    if not feats:
        return None

    current, _ = await _current_level(db, student_id=student_id, language_id=language_id)
    objectives = await get_level_curriculum(current)
    matching = [o for o in objectives if o.get("feature") in feats]
    if not matching:
        return None

    obj_ids = [o["id"] for o in matching]
    res = await db.execute(
        select(LanguageCurriculumProgress).where(
            LanguageCurriculumProgress.student_id == student_id,
            LanguageCurriculumProgress.objective_id.in_(obj_ids),
        )
    )
    by_id = {r.objective_id: r for r in res.scalars().all()}

    # Advance the first objective that is not yet mastered.
    target_obj = None
    target_row = None
    for o in matching:
        row = by_id.get(o["id"])
        if row is None or row.status != "mastered":
            target_obj, target_row = o, row
            break
    if target_obj is None:
        return None  # all objectives for this skill already mastered

    now = datetime.now(timezone.utc)
    if target_row is None:
        target_row = LanguageCurriculumProgress(
            student_id=student_id,
            language_id=language_id,
            objective_id=target_obj["id"],
            status="new",
            practice_count=0,
        )
        db.add(target_row)
    inc = 2 if score_percent >= 85 else 1
    target_row.practice_count = int(target_row.practice_count or 0) + inc
    target_row.last_practiced_at = now
    if target_row.practice_count >= PRACTICE_TO_MASTER and target_row.status != "mastered":
        target_row.status = "mastered"
        target_row.mastered_at = now
        from app.services.language_xp_service import award_language_xp

        await award_language_xp(
            db, student_id=student_id, language_id=language_id, activity="objective", key=f"objective:{target_obj['id']}"
        )
    elif target_row.status == "new":
        target_row.status = "in_progress"
    await db.flush()
    return {
        "objective_id": target_obj["id"],
        "status": target_row.status,
        "practice_count": target_row.practice_count,
    }
