"""Types for Writing Grammar Progression (W0)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing.enums import GrammarState, OfficialWritingCEFR


@dataclass(frozen=True, slots=True)
class GrammarStructureDefinition:
    """Canonical grammar spine entry."""

    structure_id: str
    label: str
    description: str
    min_cefr: OfficialWritingCEFR
    prerequisite_structure_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WritingGrammarState:
    """Per-student grammar structure mastery."""

    student_id: int
    language_id: int
    structure_id: str
    state: GrammarState
    evidence_count: int = 0
    last_seen_at: str | None = None
    introduced_at: str | None = None


@dataclass(frozen=True, slots=True)
class GrammarProgressionSnapshot:
    """Read-only snapshot for selection and coach context."""

    structures: tuple[WritingGrammarState, ...]
    learning_queue: tuple[str, ...] = ()
    practicing_queue: tuple[str, ...] = ()
