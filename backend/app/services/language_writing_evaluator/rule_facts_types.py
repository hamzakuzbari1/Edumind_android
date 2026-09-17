"""Rule-only evaluation facts — deterministic engine output before Claude merge."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing_evaluator.evaluation_facts_types import SuccessCriterionStatus
from app.services.language_writing_evaluator.evaluation_result import (
    CEFRValidationFacts,
    CompletionFacts,
    DimensionFacts,
    ExplanationFacts,
    RevisionReadinessFacts,
)

RULE_FACTS_VERSION = "8.1.0"


@dataclass(frozen=True, slots=True)
class RuleEvaluationFacts:
    """Deterministic rule engine output — owns pass/fail and technical validation."""

    draft_id: str
    revision_number: int
    chain_node_id: str
    blueprint_version: str
    blueprint_hash: str
    generation_hash: str
    word_count: int
    meets_word_limit: bool
    grammar: DimensionFacts
    vocabulary: DimensionFacts
    organization: DimensionFacts
    task_completion: DimensionFacts
    goal_alignment: DimensionFacts
    cefr_validation: CEFRValidationFacts
    success_criteria: tuple[SuccessCriterionStatus, ...]
    learning_outcomes: tuple[SuccessCriterionStatus, ...]
    revision_readiness: RevisionReadinessFacts
    completion: CompletionFacts
    explanation: ExplanationFacts
    confidence: float
    weak_skills: tuple[str, ...]
    strong_skills: tuple[str, ...]
    critical_mistakes: tuple[str, ...]
    overall_readiness: float
    rule_version: str = RULE_FACTS_VERSION
