"""Confidence influence on recommendation scoring (Phase 3.2)."""

from __future__ import annotations

from app.services.language_listening_confidence.constants import CONFIDENCE_INFLUENCE, EVIDENCE_INFLUENCE
from app.services.language_listening_confidence.evidence import plan_evidence_fill_score
from app.services.language_listening_confidence.objectives import confidence_priority_weight
from app.services.language_listening_confidence.types import ConfidenceState


def blend_with_confidence(
    curriculum_total: float,
    goal_total: float,
    confidence_factor: float,
    *,
    goal_influence: float = 0.15,
    confidence_influence: float = CONFIDENCE_INFLUENCE,
    evidence_factor: float = 0.5,
) -> tuple[float, float]:
    """Blend curriculum + goal + confidence + evidence planning."""
    conf_w = max(0.08, min(0.12, confidence_influence))
    ev_w = max(0.05, min(0.10, EVIDENCE_INFLUENCE))
    goal_w = max(0.10, min(0.16, goal_influence))
    cur_w = max(0.62, 1.0 - goal_w - conf_w - ev_w)
    blended = (
        cur_w * curriculum_total
        + goal_w * goal_total
        + conf_w * confidence_factor
        + ev_w * evidence_factor
    )
    return round(blended, 4), conf_w


def confidence_factor_for_plan(
    state: ConfidenceState,
    objectives: tuple[str, ...],
    skill_focus: tuple[str, ...],
    *,
    plan=None,
) -> float:
    obj_weight = confidence_priority_weight(state, objectives)
    skill_weight = confidence_priority_weight(state, skill_focus)
    base = 0.55 * obj_weight + 0.45 * skill_weight
    if plan is None:
        return round(base, 4)
    fill = plan_evidence_fill_score(
        narrative_format=plan.narrative_format.value,
        format_hint=plan.format_hint.value,
        category=plan.category.value,
        situation=plan.situation.value,
        difficulty_band=plan.difficulty_band.value,
        speaker_count=plan.speaker_count,
        pace=plan.pace.value,
        target_objectives=objectives + skill_focus,
        state=state,
    )
    return round(0.72 * base + 0.28 * fill, 4)
