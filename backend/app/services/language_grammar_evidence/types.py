"""Grammar Evidence contracts (G2.2) — skills emit observations; Mastery consumes them.

Skills MUST NOT calculate mastery or call Mastery write APIs directly from skill
packages without going through validated evidence observations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.language_grammar.enums import (
    GrammarEvidenceSourceSkill,
    GrammarObservationType,
)


@dataclass(frozen=True, slots=True)
class GrammarEvidenceObservation:
    """Normalized grammar evidence emitted by a skill or Grammar lesson runtime."""

    observation_id: str
    grammar_id: str
    context: str
    attempt_count: int
    correct_count: int
    observation_type: GrammarObservationType
    source_skill: GrammarEvidenceSourceSkill
    student_id: int
    language_id: int
    observed_at: str | None = None
    confidence: float | None = None
    # Optional pedagogical signals (0–100). Mastery may derive from attempts when absent.
    understanding_signal: float | None = None
    accuracy_signal: float | None = None
    fluency_signal: float | None = None
    retention_signal: float | None = None
    # Wave B completion metadata — audit/idempotency only; Mastery does not score from these.
    activity_id: str = ""
    activity_type: str = ""
    lesson_id: str = ""
    score: float | None = None


@dataclass(frozen=True, slots=True)
class GrammarEvidenceBatch:
    """Batch of observations from a single skill evaluation or Grammar step."""

    observations: tuple[GrammarEvidenceObservation, ...] = ()


class GrammarEvidenceConsumerPort(Protocol):
    """Mastery implements this — sole consumer of validated evidence."""

    def apply_evidence_batch(self, batch: GrammarEvidenceBatch) -> object:
        """Apply validated evidence; returns mastery snapshot/result."""
        ...
