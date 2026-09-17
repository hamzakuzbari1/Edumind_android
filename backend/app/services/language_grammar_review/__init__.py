"""Grammar Review (G2.3) — sole authority for review scheduling and prioritization.

RESPONSIBILITY: Review queue order, due dates, and spaced schedule policy.
Never decides progression, unlocks, or lesson order.
"""

from __future__ import annotations

from app.services.language_grammar_review.engine import (
    GrammarReviewError,
    compute_review_snapshot,
    disabled_review_snapshot,
    empty_student_state,
    format_ts,
    record_review_completed,
)
from app.services.language_grammar_review.flags import (
    grammar_engine_enabled,
    grammar_engine_select_enabled,
)
from app.services.language_grammar_review.service import (
    complete_review_and_persist,
    compute_from_mastery,
    evaluate_review_queue,
    get_review_student_state,
    selection_queue_or_empty,
)
from app.services.language_grammar_review.types import (
    GRAMMAR_REVIEW_SCHEMA_VERSION,
    GrammarReviewHistoryEntry,
    GrammarReviewItem,
    GrammarReviewQueue,
    GrammarReviewSnapshot,
    GrammarReviewStudentState,
)

PACKAGE_VERSION = "1.0.0"
RESPONSIBILITY = "Review queue order, due dates, and spaced schedule policy"

__all__ = [
    "GRAMMAR_REVIEW_SCHEMA_VERSION",
    "GrammarReviewError",
    "GrammarReviewHistoryEntry",
    "GrammarReviewItem",
    "GrammarReviewQueue",
    "GrammarReviewSnapshot",
    "GrammarReviewStudentState",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "complete_review_and_persist",
    "compute_from_mastery",
    "compute_review_snapshot",
    "disabled_review_snapshot",
    "empty_student_state",
    "evaluate_review_queue",
    "format_ts",
    "get_review_student_state",
    "grammar_engine_enabled",
    "grammar_engine_select_enabled",
    "record_review_completed",
    "selection_queue_or_empty",
]
