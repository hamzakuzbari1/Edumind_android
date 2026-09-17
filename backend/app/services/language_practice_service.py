"""Adaptive "smart review" practice, driven by the Unified Learner Model.

Targets the learner's weakest / least-evidenced knowledge components. For each pick it serves a
verified question from the bank when one exists, and generates a fresh one otherwise. Answers feed
back into the model as ``daily`` evidence, so the loop is closed: practice -> mastery -> next picks.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.enums import LanguageSkill
from app.services import language_learner_scoring as scoring
from app.services.language_engagement_service import record_activity
from app.services.language_learner_events import record_component_results
from app.services.language_learner_model_service import LanguageLearnerModelService
from app.services.language_question_generation_service import (
    generate_daily_question,
    next_placement_question,
)
from app.services.language_subscription_service import get_default_language

logger = logging.getLogger(__name__)

MAX_PRACTICE_ITEMS = 6


MASTERY_FRONTIER = 0.5  # a component counts as "reached" once mastery clears this


def _rank_weakest(profile: list[dict]) -> list[dict]:
    """Weakest mastery first; break ties by least evidence (most uncertain)."""
    return sorted(
        profile,
        key=lambda c: (round(float(c.get("p_mastery") or 0.0), 3), int(c.get("evidence_count") or 0)),
    )


def select_targets(profile: list[dict], n: int) -> list[dict]:
    """Weakest components within the learner's reach (zone of proximal development).

    Practising the *absolute* weakest would hand a beginner C1/C2 items (seeded as failures during
    placement) that are out of reach. Instead, cap targets at one CEFR band above the highest band
    the learner has actually reached, then take the weakest of those — challenging but achievable.
    """
    frontier = 0  # A1
    for c in profile:
        if float(c.get("p_mastery") or 0.0) >= MASTERY_FRONTIER:
            frontier = max(frontier, scoring.cefr_rank(c["cefr_level"]))
    reachable = [c for c in profile if scoring.cefr_rank(c["cefr_level"]) <= frontier + 1]
    return _rank_weakest(reachable or profile)[:n]


async def _question_for(db: AsyncSession, *, language_id: int, code: str, level: str, weak_point: str) -> dict | None:
    """Verified bank first, then on-the-fly generation. Returns {stem, choices, correct_index}."""
    bank = await next_placement_question(db, language_id=language_id, cefr_level=level, component_code=code)
    if bank and isinstance(bank.prompt_json, dict):
        p = bank.prompt_json
        choices = p.get("choices") or []
        if len(choices) >= 2 and p.get("correct_index") is not None:
            return {"stem": str(p.get("stem") or ""), "choices": list(choices), "correct_index": int(p["correct_index"])}
    gen = await generate_daily_question(component_code=code, cefr_level=level, weak_point=weak_point)
    if gen and gen.is_well_formed():
        return {"stem": gen.stem, "choices": gen.choices, "correct_index": gen.correct_index}
    return None


async def generate_practice_set(db: AsyncSession, *, student_id: int, count: int = 4, skill: str = "") -> dict:
    """Build a small adaptive practice set targeting the learner's weakest components.

    ``skill`` (optional) restricts practice to one skill (reading/listening/writing/speaking) — used
    when the learner taps a specific weak skill to drill it.
    """
    language = await get_default_language(db)
    service = LanguageLearnerModelService(db)
    profile = await service.get_component_profile(student_id=student_id, language_id=language.id)
    if skill:
        profile = [c for c in profile if c.get("skill") == skill]
    if not profile:
        return {"items": []}
    n = max(1, min(int(count or 4), MAX_PRACTICE_ITEMS))
    items: list[dict] = []
    for c in select_targets(profile, n):
        try:
            mcq = await _question_for(
                db, language_id=language.id, code=c["code"], level=c["cefr_level"],
                weak_point=str(c.get("category") or ""),
            )
        except Exception as exc:  # generation is best-effort — skip a component on failure
            logger.warning("practice question failed for %s: %s", c.get("code"), exc)
            mcq = None
        if mcq:
            items.append({"component_code": c["code"], "skill": c["skill"], "cefr_level": c["cefr_level"], **mcq})
    return {"items": items}


async def submit_practice(db: AsyncSession, *, student_id: int, results: list[dict]) -> dict:
    """Record answered practice questions as learner-model evidence (source='daily')."""
    language = await get_default_language(db)
    recorded = await record_component_results(
        db, student_id=student_id, language_id=language.id, results=results
    )
    correct = sum(1 for r in (results or []) if r.get("correct"))
    total = len(results or [])
    if total:
        await record_activity(
            db,
            student_id=student_id,
            language_id=language.id,
            event_type="smart_review_completed",
            skill=LanguageSkill.reading,
            payload_json={"correct": correct, "total": total},
        )
    return {"recorded": recorded, "correct": correct, "total": total}
