"""Writing Evaluation & Revision runtime (W7)."""

from __future__ import annotations

from app.services.language_writing_evaluation_runtime.pipeline import process_writing_draft_turn, process_writing_draft_turn_sync
from app.services.language_writing_evaluation_runtime.types import (
    EVALUATION_RUNTIME_VERSION,
    EvaluationRevisionTurnResult,
)

RESPONSIBILITY = "Writing evaluation and revision runtime — evaluator evaluates, coach teaches"

__all__ = [
    "EVALUATION_RUNTIME_VERSION",
    "EvaluationRevisionTurnResult",
    "RESPONSIBILITY",
    "process_writing_draft_turn",
]
