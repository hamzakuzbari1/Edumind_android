"""Writing Evaluator — hybrid rule + Claude educational analysis."""

from __future__ import annotations

from app.services.language_writing_evaluator.engine import (
    EVALUATOR_RUNTIME_VERSION,
    HYBRID_ENGINE_VERSION,
    evaluate_draft,
    evaluate_writing_draft,
    evaluate_writing_draft_sync,
    word_count,
)
from app.services.language_writing_evaluator.evaluation_result import (
    EVALUATION_RESULT_VERSION,
    WritingEvaluationEngineResult,
)
from app.services.language_writing_evaluator.rule_engine import RULE_ENGINE_VERSION, compute_rule_evaluation_facts

PACKAGE_VERSION = EVALUATION_RESULT_VERSION
RESPONSIBILITY = "Hybrid writing evaluation — rule engine + Claude educational analyzer → canonical result"

__all__ = [
    "EVALUATION_RESULT_VERSION",
    "EVALUATOR_RUNTIME_VERSION",
    "HYBRID_ENGINE_VERSION",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "RULE_ENGINE_VERSION",
    "WritingEvaluationEngineResult",
    "compute_rule_evaluation_facts",
    "evaluate_draft",
    "evaluate_writing_draft",
    "evaluate_writing_draft_sync",
    "word_count",
]
