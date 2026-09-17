"""Grammar-Constrained Evaluation contracts (V1.8).

Evaluator measures ONLY Grammar Targets. Never a general English scorer.
No Runtime / Planner / Mastery state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.services.language_grammar_activity_spec import ActivitySpecification
from app.services.language_grammar_evidence.types import GrammarEvidenceObservation

GRAMMAR_EVALUATION_SCHEMA_VERSION = 1
GRAMMAR_EVALUATION_PACKAGE_VERSION = "1.8.0"


class PatternStatus(StrEnum):
    correct = "correct"
    incorrect = "incorrect"
    missing = "missing"
    unexpected = "unexpected"
    not_applicable = "not_applicable"


class TargetStatus(StrEnum):
    correct = "correct"
    partial = "partial"
    incorrect = "incorrect"
    not_attempted = "not_attempted"


@dataclass(frozen=True, slots=True)
class LessonPackageView:
    """Minimal lesson surface for evaluation — no authoring/runtime objects."""

    expected_patterns: tuple[str, ...]
    grammar_focus: str = ""
    teacher_opening: str = ""
    main_activity: str = ""
    extras: dict[str, str] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not self.expected_patterns and not (self.grammar_focus or "").strip()


@dataclass(frozen=True, slots=True)
class GrammarEvaluationContext:
    """Canonical evaluation input — Grammar Targets define WHAT is evaluated."""

    grammar_targets: tuple[str, ...]
    expected_patterns: tuple[str, ...]
    student_response: str
    lesson_package: LessonPackageView
    specification: ActivitySpecification | None = None
    student_id: int = 0
    language_id: int = 0
    localization: str = "en"
    as_of: str = ""
    evaluation_id: str = ""
    source_skill: str = "grammar_lesson"
    extras: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GrammarEvaluationRequest:
    """Public evaluation request envelope."""

    context: GrammarEvaluationContext
    request_id: str = ""


@dataclass(frozen=True, slots=True)
class PatternEvaluationResult:
    """One expected-pattern evaluation — never general English metrics."""

    pattern: str
    grammar_target: str
    status: PatternStatus
    confidence: float
    reason: str = ""
    source_sentence: str = ""


@dataclass(frozen=True, slots=True)
class TargetEvaluationResult:
    """Per-Grammar-Target evaluation aggregate."""

    target_id: str
    status: TargetStatus
    confidence: float
    matched_patterns: tuple[str, ...] = ()
    missing_patterns: tuple[str, ...] = ()
    unexpected_patterns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GrammarEvidenceItem:
    """Structured grammar evidence item before observation mapping."""

    grammar_target: str
    pattern: str
    correct: bool
    confidence: float
    reason: str
    source_sentence: str = ""
    timestamp: str = ""


@dataclass(frozen=True, slots=True)
class GrammarEvaluationResult:
    """Evaluator output — evidence observations only; never mastery writes."""

    evaluation_id: str
    target_results: tuple[TargetEvaluationResult, ...]
    pattern_results: tuple[PatternEvaluationResult, ...]
    evidence_items: tuple[GrammarEvidenceItem, ...]
    observations: tuple[GrammarEvidenceObservation, ...]
    request_fingerprint: str
    evaluation_version: str = GRAMMAR_EVALUATION_PACKAGE_VERSION
    schema_version: int = GRAMMAR_EVALUATION_SCHEMA_VERSION
    notes: str = ""
