"""Grammar Progression (G2.1 + patch) — sole authority for current/next/unlock/candidate/stretch.

RESPONSIBILITY: Deterministic progression decisions from official_overall_cefr,
Grammar Catalog, and student grammar snapshot. No mastery scoring, review,
planner, runtime, or Claude.
"""

from __future__ import annotations

from app.services.language_grammar_progression.engine import (
    GrammarProgressionError,
    compute_progression_snapshot,
    disabled_snapshot,
)
from app.services.language_grammar_progression.flags import (
    grammar_engine_enabled,
    grammar_engine_select_enabled,
)
from app.services.language_grammar_progression.service import (
    compute_from_state,
    evaluate_and_persist_grammar_progression,
    get_grammar_progression_snapshot,
    load_grammar_progression_snapshot_readonly,
    record_grammar_topic_cleared,
    record_grammar_topic_completed,
    selection_snapshot_or_disabled,
)
from app.services.language_grammar_progression.types import (
    GRAMMAR_PROGRESSION_SCHEMA_VERSION,
    STRETCH_EARLY_TOPIC_LIMIT,
    GrammarCandidatePriorityEntry,
    GrammarProgressionSnapshot,
    GrammarProgressionStudentState,
)

PACKAGE_VERSION = "1.1.0"
RESPONSIBILITY = (
    "Deterministic current/next/unlock/candidate/stretch from official_overall_cefr "
    "+ catalog + student grammar snapshot"
)

__all__ = [
    "GRAMMAR_PROGRESSION_SCHEMA_VERSION",
    "GrammarCandidatePriorityEntry",
    "GrammarProgressionError",
    "GrammarProgressionSnapshot",
    "GrammarProgressionStudentState",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "STRETCH_EARLY_TOPIC_LIMIT",
    "compute_from_state",
    "compute_progression_snapshot",
    "disabled_snapshot",
    "evaluate_and_persist_grammar_progression",
    "get_grammar_progression_snapshot",
    "grammar_engine_enabled",
    "grammar_engine_select_enabled",
    "load_grammar_progression_snapshot_readonly",
    "record_grammar_topic_cleared",
    "record_grammar_topic_completed",
    "selection_snapshot_or_disabled",
]
