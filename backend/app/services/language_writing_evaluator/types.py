"""Types for Writing Evaluator (W2) — facts only, no coach narrative."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EvaluationDimension(StrEnum):
    """Canonical rubric dimensions — identical regardless of coach personality."""

    task_achievement = "task_achievement"
    coherence = "coherence"
    grammar = "grammar"
    lexis = "lexis"
    register = "register"
    organization = "organization"


class EvaluationIssueCategory(StrEnum):
    """Tagged issue categories aligned with W1.2 common_mistakes."""

    grammar = "grammar"
    vocabulary = "vocabulary"
    organization = "organization"
    tone = "tone"
    formatting = "formatting"
    task = "task"


@dataclass(frozen=True, slots=True)
class EvaluationIssue:
    """Single detected educational issue — fact, not feedback copy."""

    category: EvaluationIssueCategory
    code: str
    description_internal: str
    severity: float  # 0.0–1.0
    matched_node_mistake: str = ""


@dataclass(frozen=True, slots=True)
class EvaluationStrength:
    """Single detected strength — fact, not praise copy."""

    dimension: EvaluationDimension
    code: str
    description_internal: str


@dataclass(frozen=True, slots=True)
class DimensionScore:
    """Per-dimension educational score — internal only."""

    dimension: EvaluationDimension
    score: float  # 0.0–1.0
    evidence_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WritingEvaluationResult:
    """Complete evaluator output for one draft — coach must not recompute rubric.

    Pipeline position: Student draft → Evaluator → Facts → Narrative → Coach.
    """

    draft_id: str
    chain_node_id: str
    dimension_scores: tuple[DimensionScore, ...]
    issues: tuple[EvaluationIssue, ...]
    strengths: tuple[EvaluationStrength, ...]
    priority_issue: EvaluationIssue | None
    task_completion_ratio: float
    word_count: int
    meets_minimum_length: bool
    ready_to_complete_signal: bool
    evaluator_version: str = "2.0.0"

    def to_facts_dict(self) -> dict[str, object]:
        """Internal facts serialization — not student-facing."""
        return {
            "draft_id": self.draft_id,
            "chain_node_id": self.chain_node_id,
            "dimension_scores": [
                {"dimension": d.dimension.value, "score": round(d.score, 4), "evidence_codes": list(d.evidence_codes)}
                for d in self.dimension_scores
            ],
            "issues": [
                {
                    "category": i.category.value,
                    "code": i.code,
                    "description_internal": i.description_internal,
                    "severity": round(i.severity, 4),
                    "matched_node_mistake": i.matched_node_mistake,
                }
                for i in self.issues
            ],
            "strengths": [
                {"dimension": s.dimension.value, "code": s.code, "description_internal": s.description_internal}
                for s in self.strengths
            ],
            "priority_issue": (
                {
                    "category": self.priority_issue.category.value,
                    "code": self.priority_issue.code,
                    "description_internal": self.priority_issue.description_internal,
                    "severity": round(self.priority_issue.severity, 4),
                }
                if self.priority_issue
                else None
            ),
            "task_completion_ratio": round(self.task_completion_ratio, 4),
            "word_count": self.word_count,
            "meets_minimum_length": self.meets_minimum_length,
            "ready_to_complete_signal": self.ready_to_complete_signal,
            "evaluator_version": self.evaluator_version,
        }


@dataclass(frozen=True, slots=True)
class EvaluatorInputContext:
    """Inputs required for evaluation — metadata only in W2 (no runtime)."""

    chain_id: str
    chain_node_id: str
    task_type: str
    genre: str
    learning_outcomes: tuple[str, ...]
    common_mistakes: tuple[str, ...]
    difficulty_drivers: tuple[str, ...]
    grammar_focus_primary: str
    min_words: int
    max_words: int
