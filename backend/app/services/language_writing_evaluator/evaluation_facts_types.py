"""Canonical Evaluation Facts (W7) — persisted facts only; no educational narrative."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

EVALUATION_FACTS_VERSION = "7.0.0"


class CriterionStatus(StrEnum):
    met = "met"
    partial = "partial"
    not_met = "not_met"


@dataclass(frozen=True, slots=True)
class DimensionResult:
    """Single rubric dimension result — internal fact."""

    dimension: str
    score: float
    weight: float
    passed: bool
    evidence_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SuccessCriterionStatus:
    label: str
    status: CriterionStatus
    code: str = ""


@dataclass(frozen=True, slots=True)
class WritingEvaluationFacts:
    """Canonical evaluation facts — no student-facing coaching copy."""

    draft_id: str
    revision_number: int
    blueprint_version: str
    blueprint_hash: str
    generation_hash: str
    grammar_result: DimensionResult
    vocabulary_result: DimensionResult
    organization_result: DimensionResult
    task_completion_result: DimensionResult
    goal_alignment_result: DimensionResult
    word_count: int
    meets_word_limit: bool
    critical_mistakes: tuple[str, ...]
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    success_criteria_status: tuple[SuccessCriterionStatus, ...]
    learning_outcomes_status: tuple[SuccessCriterionStatus, ...]
    overall_readiness: float
    ready_to_complete: bool
    evaluator_version: str = EVALUATION_FACTS_VERSION

    def to_persistence_dict(self) -> dict[str, object]:
        def _dim(d: DimensionResult) -> dict[str, object]:
            return {
                "dimension": d.dimension,
                "score": round(d.score, 4),
                "weight": round(d.weight, 4),
                "passed": d.passed,
                "evidence_codes": list(d.evidence_codes),
            }

        def _criteria(items: tuple[SuccessCriterionStatus, ...]) -> list[dict[str, object]]:
            return [{"label": i.label, "status": i.status.value, "code": i.code} for i in items]

        return {
            "draft_id": self.draft_id,
            "revision_number": self.revision_number,
            "blueprint_version": self.blueprint_version,
            "blueprint_hash": self.blueprint_hash,
            "generation_hash": self.generation_hash,
            "grammar_result": _dim(self.grammar_result),
            "vocabulary_result": _dim(self.vocabulary_result),
            "organization_result": _dim(self.organization_result),
            "task_completion_result": _dim(self.task_completion_result),
            "goal_alignment_result": _dim(self.goal_alignment_result),
            "word_count": self.word_count,
            "meets_word_limit": self.meets_word_limit,
            "critical_mistakes": list(self.critical_mistakes),
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "success_criteria_status": _criteria(self.success_criteria_status),
            "learning_outcomes_status": _criteria(self.learning_outcomes_status),
            "overall_readiness": round(self.overall_readiness, 4),
            "ready_to_complete": self.ready_to_complete,
            "evaluator_version": self.evaluator_version,
        }
