"""Ownership guard — educational decisions forbidden from author adapters."""

from __future__ import annotations

AUTHOR_FORBIDDEN_DECISIONS: frozenset[str] = frozenset(
    {
        "official_cefr",
        "learning_stage",
        "mission_selection",
        "vocabulary_target_selection",
        "grammar_topic_selection",
        "objectives",
        "promotion",
        "readiness",
        "mastery_scoring",
        "evidence_application",
    }
)
