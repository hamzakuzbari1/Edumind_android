"""Types for Grammar Analytics (G0) — never writes mastery or progression."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_grammar.enums import GrammarCEFRBand, GrammarMasteryState
from app.services.language_grammar_mastery.types import (
    GrammarMasteryDimensions,
    PublicGrammarMasteryView,
)
from app.services.language_grammar_progression.types import GrammarProgressionSnapshot


@dataclass(frozen=True, slots=True)
class GrammarTopicAnalyticsRow:
    """Hub/parent row — public overall by default."""

    public: PublicGrammarMasteryView
    # Optional admin/analytics-only internal dimensions (never default student surface).
    internal_dimensions: GrammarMasteryDimensions | None = None


@dataclass(frozen=True, slots=True)
class GrammarAnalyticsProjection:
    """Aggregated read model for hub/parent panels."""

    student_id: int
    language_id: int
    anchor_cefr: GrammarCEFRBand
    progression: GrammarProgressionSnapshot
    topics: tuple[GrammarTopicAnalyticsRow, ...] = ()
    mastered_count: int = 0
    learning_count: int = 0
    practicing_count: int = 0
    unknown_count: int = 0


def count_by_state(states: tuple[GrammarMasteryState, ...]) -> dict[str, int]:
    """Helper for projection assembly (G5); pure function, no I/O."""
    counts = {s.value: 0 for s in GrammarMasteryState}
    for state in states:
        counts[state.value] = counts.get(state.value, 0) + 1
    return counts
