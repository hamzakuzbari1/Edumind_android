"""Grammar Progression contracts (G2.1 + patch).

Progression owns current/next/unlock/candidate/stretch decisions only.
Does not own mastery, review, planner, runtime, or Claude.

``completed_ids`` (renamed from cleared_ids): progression-lifecycle gate meaning
"topic finished enough that descendants may unlock". Distinct from Mastery
dimension scores / ``mastered`` state — Mastery decides proficiency; Progression
only stores this unlock-enabling completion set (often synced when Mastery
marks a topic mastered).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_grammar.enums import GrammarCandidatePriority, GrammarCEFRBand

GRAMMAR_PROGRESSION_SCHEMA_VERSION = 2
# Max early topics from the next CEFR band when stretch is explicitly allowed.
STRETCH_EARLY_TOPIC_LIMIT = 2


@dataclass(frozen=True, slots=True)
class GrammarProgressionStudentState:
    """Persisted student grammar snapshot inputs for Progression (not mastery scores).

    ``completed_ids`` — topics finished for unlock purposes (descendants may unlock).
    Not a mastery score store; see module docstring.

    ``unlocked_ids`` — monotonically growing unlock set (unlocked remain unlocked).

    ``current_grammar_id`` — optional sticky current when still valid.
    """

    student_id: int
    language_id: int
    completed_ids: frozenset[str] = frozenset()
    unlocked_ids: frozenset[str] = frozenset()
    current_grammar_id: str | None = None
    stretch_allowed: bool = False


@dataclass(frozen=True, slots=True)
class GrammarCandidatePriorityEntry:
    """One topic with its progression-queue priority."""

    grammar_id: str
    priority: GrammarCandidatePriority


@dataclass(frozen=True, slots=True)
class GrammarProgressionSnapshot:
    """Deterministic progression read model — identical inputs ⇒ identical output."""

    anchor_cefr: GrammarCEFRBand
    current_grammar_id: str | None
    next_grammar_id: str | None
    unlocked_ids: tuple[str, ...]
    locked_ids: tuple[str, ...]
    future_ids: tuple[str, ...]
    stretch_ids: tuple[str, ...]
    candidate_pool_ids: tuple[str, ...]
    candidate_priorities: tuple[GrammarCandidatePriorityEntry, ...]
    progression_reason: tuple[str, ...]
    stretch_allowed: bool = False
    schema_version: int = GRAMMAR_PROGRESSION_SCHEMA_VERSION
    enabled: bool = True
