"""Completion decision — deprecated; eligibility is computed in canonical evaluation engine."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing_evaluator.evaluation_facts_types import WritingEvaluationFacts
from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult

COMPLETION_VERSION = "8.0.0"


@dataclass(frozen=True, slots=True)
class CompletionDecision:
    completed: bool
    ready_to_complete: bool
    criteria_met_count: int
    criteria_total: int
    outcomes_met_count: int
    outcomes_total: int
    reason: str
    completion_version: str = COMPLETION_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "completed": self.completed,
            "ready_to_complete": self.ready_to_complete,
            "eligible": self.completed,
            "criteria_met_count": self.criteria_met_count,
            "criteria_total": self.criteria_total,
            "outcomes_met_count": self.outcomes_met_count,
            "outcomes_total": self.outcomes_total,
            "reason": self.reason,
            "completion_version": self.completion_version,
        }


def completion_from_evaluation(evaluation: WritingEvaluationEngineResult) -> CompletionDecision:
    """Render-only adapter from canonical evaluation."""
    c = evaluation.completion
    return CompletionDecision(
        completed=c.eligible,
        ready_to_complete=c.eligible,
        criteria_met_count=c.criteria_met_count,
        criteria_total=c.criteria_total,
        outcomes_met_count=c.outcomes_met_count,
        outcomes_total=c.outcomes_total,
        reason=c.reason,
    )


def decide_completion(
    facts: WritingEvaluationFacts,
    blueprint: object,
) -> CompletionDecision:
    """Deprecated — rebuilds minimal decision from legacy facts only."""
    _ = blueprint
    return CompletionDecision(
        completed=facts.ready_to_complete,
        ready_to_complete=facts.ready_to_complete,
        criteria_met_count=sum(1 for c in facts.success_criteria_status if c.status.value == "met"),
        criteria_total=len(facts.success_criteria_status),
        outcomes_met_count=sum(1 for o in facts.learning_outcomes_status if o.status.value == "met"),
        outcomes_total=len(facts.learning_outcomes_status),
        reason="Legacy facts adapter",
    )
