"""SPA PASS/FAIL aggregation — aggregate gate AND mandatory competency gate (S19).

Hard rule: PASS requires aggregate.passed AND mandatory_all_met.
A mandatory competency failure blocks PASS even when aggregate would pass.

Does not invent product thresholds. Per-task signals reuse S7 facts
(completion_eligible / semantic_task_met / overall_readiness).
Does not write official_speaking_cefr.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.language_speaking_promotion_test.bridge import build_bridge_recommendation
from app.services.language_speaking_promotion_test.execution_types import (
    SpaAggregatePerformance,
    SpaAssessmentOutcome,
    SpaAssessmentResult,
    SpaMandatoryCompetencyKind,
    SpaMandatoryCompetencyOutcome,
    SpaMandatoryCompetencyRequirement,
    SpaPassGateDecision,
    SpaTaskScoreSummary,
)


def evaluate_aggregate_performance(
    scores: tuple[SpaTaskScoreSummary, ...] | list[SpaTaskScoreSummary],
    *,
    tasks_total: int,
) -> SpaAggregatePerformance:
    """Structural aggregate gate from S7 task score summaries (no SPA thresholds)."""
    scored = tuple(scores)
    n = len(scored)
    if n == 0 or tasks_total <= 0 or n < tasks_total:
        return SpaAggregatePerformance(
            tasks_scored=n,
            tasks_total=tasks_total,
            mean_overall_readiness=None,
            tasks_completion_eligible=0,
            passed=False,
            reason="not_all_tasks_scored",
        )
    eligible = sum(1 for s in scored if s.completion_eligible)
    mean = sum(float(s.overall_readiness) for s in scored) / n
    # Aggregate performance: every frozen task scored and S7-completion-eligible.
    # Numeric bar thresholds remain product policy (not introduced here).
    passed = eligible == tasks_total
    return SpaAggregatePerformance(
        tasks_scored=n,
        tasks_total=tasks_total,
        mean_overall_readiness=mean,
        tasks_completion_eligible=eligible,
        passed=passed,
        reason="all_tasks_completion_eligible" if passed else "aggregate_completion_incomplete",
    )


def evaluate_mandatory_competencies(
    *,
    requirements: tuple[SpaMandatoryCompetencyRequirement, ...] | list[SpaMandatoryCompetencyRequirement],
    scores: tuple[SpaTaskScoreSummary, ...] | list[SpaTaskScoreSummary],
) -> tuple[SpaMandatoryCompetencyOutcome, ...]:
    by_task = {s.task_id: s for s in scores}
    outcomes: list[SpaMandatoryCompetencyOutcome] = []
    for req in requirements:
        linked = [by_task[tid] for tid in req.task_ids if tid in by_task]
        if not req.task_ids:
            outcomes.append(
                SpaMandatoryCompetencyOutcome(
                    requirement_id=req.requirement_id,
                    kind=req.kind,
                    met=False,
                    reason="no_linked_tasks",
                )
            )
            continue
        if len(linked) < len(req.task_ids):
            outcomes.append(
                SpaMandatoryCompetencyOutcome(
                    requirement_id=req.requirement_id,
                    kind=req.kind,
                    met=False,
                    reason="linked_task_unscored",
                )
            )
            continue

        if req.kind == SpaMandatoryCompetencyKind.required_production_competency:
            met = all(s.semantic_task_met for s in linked)
            reason = "production_semantic_met" if met else "production_semantic_unmet"
        elif req.kind == SpaMandatoryCompetencyKind.required_task_family:
            met = all(s.completion_eligible for s in linked)
            reason = "family_eligible" if met else "family_not_eligible"
        else:  # required_skill_group
            # Structural skill-group gate: linked tasks completion-eligible.
            # Richer skill scoring remains product policy.
            met = all(s.completion_eligible for s in linked)
            reason = "skill_group_met" if met else "skill_group_unmet"

        outcomes.append(
            SpaMandatoryCompetencyOutcome(
                requirement_id=req.requirement_id,
                kind=req.kind,
                met=met,
                reason=reason,
            )
        )
    return tuple(outcomes)


def decide_spa_pass_gate(
    *,
    scores: tuple[SpaTaskScoreSummary, ...] | list[SpaTaskScoreSummary],
    tasks_total: int,
    requirements: tuple[SpaMandatoryCompetencyRequirement, ...] | list[SpaMandatoryCompetencyRequirement],
) -> SpaPassGateDecision:
    aggregate = evaluate_aggregate_performance(scores, tasks_total=tasks_total)
    mandatory_outcomes = evaluate_mandatory_competencies(requirements=requirements, scores=scores)
    mandatory_all_met = bool(mandatory_outcomes) and all(o.met for o in mandatory_outcomes)
    if not mandatory_outcomes:
        # No declared mandatories → architecture still requires explicit aggregate PASS only.
        mandatory_all_met = True
    blocked = aggregate.passed and not mandatory_all_met
    if aggregate.passed and mandatory_all_met:
        outcome = SpaAssessmentOutcome.PASS
    else:
        outcome = SpaAssessmentOutcome.FAIL
    return SpaPassGateDecision(
        aggregate=aggregate,
        mandatory_requirements=tuple(requirements),
        mandatory_outcomes=mandatory_outcomes,
        mandatory_all_met=mandatory_all_met,
        would_pass_on_aggregate_alone=aggregate.passed,
        blocked_by_mandatory_competency=blocked,
        outcome=outcome,
    )


def build_assessment_result(
    *,
    assessment_id: str,
    attempt_id: str,
    blueprint_id: str,
    outcome: SpaAssessmentOutcome,
    pass_gate: SpaPassGateDecision | None,
    scores: tuple[SpaTaskScoreSummary, ...] | list[SpaTaskScoreSummary] = (),
    completed_at: str | None = None,
) -> SpaAssessmentResult:
    ts = completed_at or datetime.now(timezone.utc).isoformat()
    ready = outcome == SpaAssessmentOutcome.PASS
    bridge = None
    if outcome == SpaAssessmentOutcome.FAIL and pass_gate is not None:
        bridge = build_bridge_recommendation(pass_gate=pass_gate, scores=scores)
    return SpaAssessmentResult(
        assessment_id=assessment_id,
        attempt_id=attempt_id,
        blueprint_id=blueprint_id,
        outcome=outcome,
        pass_gate=pass_gate,
        bridge_recommendation=bridge,
        ready_for_official_promotion=ready,
        completed_at=ts,
    )
