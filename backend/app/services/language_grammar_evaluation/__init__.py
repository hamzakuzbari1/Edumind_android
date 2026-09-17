"""Grammar-Constrained Evaluation (V1.8).

RESPONSIBILITY: Evaluate ONLY Grammar Targets / lesson expected patterns.
Emit GrammarEvidenceObservation only. Never general English scoring.
Never writes Mastery / Progression / Review / Planner / Runtime.
"""

from __future__ import annotations

from app.services.language_grammar_evaluation.engine import (
    build_evaluation_request,
    evaluate_grammar,
)
from app.services.language_grammar_evaluation.errors import (
    EvaluationDisabledError,
    EvaluationValidationError,
    GrammarEvaluationError,
)
from app.services.language_grammar_evaluation.evidence_mapper import (
    evidence_items_to_observations,
    pattern_results_to_evidence_items,
)
from app.services.language_grammar_evaluation.fingerprint import fingerprint_evaluation_request
from app.services.language_grammar_evaluation.flags import (
    grammar_engine_enabled,
    grammar_evaluation_enabled,
    grammar_evaluation_strict,
)
from app.services.language_grammar_evaluation.lesson_view import (
    lesson_view_from_payload,
    lesson_view_from_specification,
)
from app.services.language_grammar_evaluation.pattern_matching import (
    assign_pattern_to_target,
    evaluate_pattern,
    normalize_text,
    pattern_stem,
)
from app.services.language_grammar_evaluation.types import (
    GRAMMAR_EVALUATION_PACKAGE_VERSION,
    GRAMMAR_EVALUATION_SCHEMA_VERSION,
    GrammarEvaluationContext,
    GrammarEvaluationRequest,
    GrammarEvaluationResult,
    GrammarEvidenceItem,
    LessonPackageView,
    PatternEvaluationResult,
    PatternStatus,
    TargetEvaluationResult,
    TargetStatus,
)
from app.services.language_grammar_evaluation.validation import (
    detect_unexpected_grammar_in_text,
    validate_evaluation_request,
    validate_evidence_items,
)
from app.services.language_grammar_evidence.types import GrammarEvidenceObservation

PACKAGE_VERSION = GRAMMAR_EVALUATION_PACKAGE_VERSION
RESPONSIBILITY = (
    "Grammar-Constrained Evaluation — score Grammar Targets / lesson patterns only; "
    "emit evidence observations; never mastery/progression/review writes"
)

__all__ = [
    "GRAMMAR_EVALUATION_PACKAGE_VERSION",
    "GRAMMAR_EVALUATION_SCHEMA_VERSION",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "EvaluationDisabledError",
    "EvaluationValidationError",
    "GrammarEvaluationContext",
    "GrammarEvaluationError",
    "GrammarEvaluationRequest",
    "GrammarEvaluationResult",
    "GrammarEvidenceItem",
    "GrammarEvidenceObservation",
    "LessonPackageView",
    "PatternEvaluationResult",
    "PatternStatus",
    "TargetEvaluationResult",
    "TargetStatus",
    "assign_pattern_to_target",
    "build_evaluation_request",
    "detect_unexpected_grammar_in_text",
    "evaluate_grammar",
    "evaluate_pattern",
    "evidence_items_to_observations",
    "fingerprint_evaluation_request",
    "grammar_engine_enabled",
    "grammar_evaluation_enabled",
    "grammar_evaluation_strict",
    "lesson_view_from_payload",
    "lesson_view_from_specification",
    "normalize_text",
    "pattern_results_to_evidence_items",
    "pattern_stem",
    "validate_evaluation_request",
    "validate_evidence_items",
]
