"""Phase 4 — Learning Coach Agent.

Synthesises the learner's full state — memory (Phase 1), recurring errors (Phase 2) and the
difficulty profile (Phase 3) — into one personalized recommendation via Gemini, with a deterministic
fallback so the endpoint always returns something useful (even with no AI key). Cached per learner
(in-memory TTL) to avoid re-calling Gemini on every page load. NO new tables; feedback is stored in
`LanguageStudentProfile.preferences_json`.
"""

from __future__ import annotations

import json
import logging
import re
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_locale import GEMINI_LANGUAGE_RULE
from app.models.language.profile import LanguageStudentProfile
from app.services import language_difficulty_service as difficulty_service
from app.services import language_error_intelligence_service as error_service
from app.services import language_learner_memory_service as memory_service
from app.services.ai_service import generate_llm_json
from app.services.language_conversation_prompts import level_calibration_line

logger = logging.getLogger(__name__)

_CACHE_TTL = 60 * 60  # 1 hour (per the master prompt's caching targets)
_cache: dict[tuple[int, int], tuple[float, dict]] = {}

_SYSTEM = (
    "You are a supportive, practical English learning coach for Syrian secondary-school learners. "
    "Given the learner's memory, recurring mistakes and difficulty profile, recommend the single most "
    "useful next focus — concrete, encouraging and achievable. English only. "
    f"{GEMINI_LANGUAGE_RULE} "
    "Return ONLY valid JSON with EXACTLY these keys: primary_weakness, secondary_weakness, "
    "recommended_lesson, recommended_activity, recommended_vocabulary (list of up to 5 words), "
    "weekly_goal, estimated_improvement_area, coaching_message, reasoning. No markdown, no code fences."
)

_OUTPUT_KEYS = (
    "primary_weakness",
    "secondary_weakness",
    "recommended_lesson",
    "recommended_activity",
    "recommended_vocabulary",
    "weekly_goal",
    "estimated_improvement_area",
    "coaching_message",
    "reasoning",
)

# Map the weakest skill dimension to a concrete practice activity.
_ACTIVITY_FOR_DIM = {
    "reading": "a short reading passage with comprehension questions",
    "listening": "a listening clip with comprehension questions",
    "writing": "a short guided writing task",
    "speaking": "a free-chat speaking session",
    "grammar": "a focused grammar micro-lesson",
    "vocabulary": "a vocabulary review session",
}


# --------------------------------------------------------------------------------------------------
# Pure helpers (no I/O — unit-tested directly)
# --------------------------------------------------------------------------------------------------
def _parse(raw: str) -> dict | None:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        data = json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def normalize_recommendation(data: dict | None) -> dict | None:
    """Coerce a raw model dict into the exact output shape, or None if unusable."""
    if not isinstance(data, dict):
        return None
    out: dict = {}
    for k in _OUTPUT_KEYS:
        v = data.get(k)
        if k == "recommended_vocabulary":
            out[k] = [str(w).strip() for w in v][:5] if isinstance(v, list) else []
        else:
            out[k] = str(v).strip() if v is not None else ""
    # A recommendation with no actionable content is not useful.
    if not (out["coaching_message"] or out["weekly_goal"] or out["primary_weakness"]):
        return None
    return out


def weakest_dimension(difficulty: dict) -> str | None:
    """The dimension with the lowest (most negative) modifier that actually has evidence."""
    modifiers = (difficulty or {}).get("modifiers") or {}
    scores = (difficulty or {}).get("scores") or {}
    present = {d: m for d, m in modifiers.items() if scores.get(d) is not None}
    if not present:
        return None
    return min(present, key=lambda d: present[d])


def build_context_block(memory: dict, report: dict, difficulty: dict) -> str:
    """Compact context block fed to the coach prompt."""
    lines: list[str] = []
    interests = (memory or {}).get("interests") or (memory or {}).get("favorite_topics") or []
    goals = (memory or {}).get("learning_goals") or []
    weaknesses = (memory or {}).get("derived_weaknesses") or []
    if interests:
        lines.append(f"Interests: {', '.join(interests)}")
    if goals:
        lines.append(f"Stated goals: {', '.join(goals)}")
    if weaknesses:
        lines.append(f"Weak areas: {', '.join(weaknesses)}")
    if report:
        if report.get("recommended_focus"):
            lines.append(f"Most recurring mistake: {report['recommended_focus']}")
        if report.get("trend"):
            lines.append(f"Error trend: {report['trend']}")
    if difficulty:
        lines.append(f"Effective level: {difficulty.get('effective_level')}")
        lines.append(f"Recommended complexity: {difficulty.get('recommended_complexity')}")
    return "\n".join(lines) if lines else "No history yet — the learner is just getting started."


def fallback_recommendation(memory: dict, report: dict, difficulty: dict) -> dict:
    """Deterministic recommendation from the data — used when AI is unavailable/invalid."""
    weaknesses = (memory or {}).get("derived_weaknesses") or []
    focus = (report or {}).get("recommended_focus") or (weaknesses[0] if weaknesses else "")
    secondary = weaknesses[1] if len(weaknesses) > 1 else ""
    dim = weakest_dimension(difficulty or {})
    activity = _ACTIVITY_FOR_DIM.get(dim or "", "a short practice session")
    level = (difficulty or {}).get("effective_level") or (difficulty or {}).get("cefr_level") or ""
    primary = focus or (dim or "general practice")
    goal = f"This week, practise {primary} with {activity} on most days."
    return {
        "primary_weakness": primary,
        "secondary_weakness": secondary,
        "recommended_lesson": f"{dim or 'core'} lesson at level {level}".strip(),
        "recommended_activity": activity,
        "recommended_vocabulary": [],
        "weekly_goal": goal,
        "estimated_improvement_area": dim or primary,
        "coaching_message": "Small, steady steps add up — focus on one thing at a time and keep going!",
        "reasoning": "Generated from your recent mistakes and skill profile.",
    }


# --------------------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------------------
async def _gather_context(db: AsyncSession, *, student_id: int, language_id: int) -> tuple[dict, dict, dict]:
    memory = await memory_service.get_memory(db, student_id=student_id, language_id=language_id)
    report = await error_service.generate_weakness_report(db, student_id=student_id, language_id=language_id)
    difficulty = await difficulty_service.calculate_modifier(db, student_id=student_id, language_id=language_id)
    return memory, report, difficulty


async def get_recommendation(
    db: AsyncSession, *, student_id: int, language_id: int, refresh: bool = False
) -> dict:
    """Personalized coaching recommendation (cached). Falls back to a deterministic one on AI failure."""
    cache_key = (student_id, language_id)
    if not refresh:
        hit = _cache.get(cache_key)
        if hit and hit[0] > time.time():
            return hit[1]

    memory, report, difficulty = await _gather_context(db, student_id=student_id, language_id=language_id)
    fallback = fallback_recommendation(memory, report, difficulty)

    result = fallback
    level = difficulty.get("cefr_level") or "A1"
    try:
        prompt = (
            "Learner profile:\n"
            + build_context_block(memory, report, difficulty)
            + level_calibration_line(level)
            + "\nRecommend the single most useful next focus now."
        )
        raw = await generate_llm_json(prompt, system=_SYSTEM, temperature=0.5, max_output_tokens=900)
        normalized = normalize_recommendation(_parse(raw))
        if normalized is not None:
            # Keep a deterministic vocabulary fallback if the model returned none.
            if not normalized["recommended_vocabulary"]:
                normalized["recommended_vocabulary"] = fallback["recommended_vocabulary"]
            result = normalized
    except Exception as exc:  # pragma: no cover - LLM variance
        logger.warning("coach recommendation AI failed (student=%s): %s", student_id, exc)

    _cache[cache_key] = (time.time() + _CACHE_TTL, result)
    return result


async def get_weekly_goal(db: AsyncSession, *, student_id: int, language_id: int) -> dict:
    """Just the current week's goal (reuses the cached recommendation)."""
    rec = await get_recommendation(db, student_id=student_id, language_id=language_id)
    return {"weekly_goal": rec.get("weekly_goal", ""), "primary_weakness": rec.get("primary_weakness", "")}


async def record_feedback(
    db: AsyncSession, *, student_id: int, language_id: int, rating: str, note: str = ""
) -> dict:
    """Store the learner's rating of a recommendation in preferences_json (rolling, capped)."""
    profile = (
        await db.execute(
            select(LanguageStudentProfile).where(
                LanguageStudentProfile.student_id == student_id,
                LanguageStudentProfile.language_id == language_id,
            )
        )
    ).scalar_one_or_none()
    if profile is None:
        profile = LanguageStudentProfile(student_id=student_id, language_id=language_id)
        db.add(profile)
        await db.flush()
    prefs = dict(profile.preferences_json or {})
    feedback = list(prefs.get("coach_feedback") or [])
    feedback.append({"rating": (rating or "").strip()[:20], "note": (note or "").strip()[:200], "at": time.time()})
    prefs["coach_feedback"] = feedback[-20:]
    profile.preferences_json = prefs
    await db.flush()
    return {"ok": True}
