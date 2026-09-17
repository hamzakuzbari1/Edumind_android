"""Student-safe FAIL bridge recommendation projection (S19).

Owns recommendation copy only — does not create lessons or mutate planner.
"""

from __future__ import annotations

from app.services.language_speaking_promotion_test.execution_types import (
    SpaBridgeRecommendation,
    SpaPassGateDecision,
    SpaTaskScoreSummary,
)


def build_bridge_recommendation(
    *,
    pass_gate: SpaPassGateDecision,
    scores: tuple[SpaTaskScoreSummary, ...] | list[SpaTaskScoreSummary],
) -> SpaBridgeRecommendation:
    failed = tuple(o.requirement_id for o in pass_gate.mandatory_outcomes if not o.met)
    weak: list[str] = []
    for s in scores:
        for sid in s.weak_skills:
            if sid not in weak:
                weak.append(sid)
        if s.priority_issue and s.priority_issue not in weak:
            weak.append(s.priority_issue)

    focus_ids = tuple(weak[:6]) if weak else tuple(
        tid for req in pass_gate.mandatory_requirements if req.requirement_id in failed for tid in req.target_ids
    )[:6]
    labels = tuple(focus_ids)
    practice: list[str] = []
    if pass_gate.blocked_by_mandatory_competency:
        practice.append("Practice the required competencies that blocked promotion.")
    if not pass_gate.aggregate.passed:
        practice.append("Complete full responses for every assessment task.")
    practice.append("Return to guided speaking practice, then retry when ready.")

    summary = (
        "Required competencies were not met in this assessment."
        if pass_gate.blocked_by_mandatory_competency
        else "Overall assessment performance did not meet the promotion bar."
    )
    return SpaBridgeRecommendation(
        focus_skill_ids=focus_ids,
        focus_labels=labels,
        summary=summary,
        suggested_practice=tuple(practice),
        failed_competency_ids=failed,
    )
