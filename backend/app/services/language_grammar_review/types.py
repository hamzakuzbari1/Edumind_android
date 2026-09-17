"""Grammar Review types (G2.3) — schedule + queue; no lesson planning."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_grammar.enums import (
    GrammarReviewMode,
    GrammarReviewPriority,
    GrammarReviewReason,
)

GRAMMAR_REVIEW_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class GrammarReviewHistoryEntry:
    """Durable per-topic review history (inputs only — not derived queue rows)."""

    grammar_id: str
    last_reviewed_at: str | None = None
    review_count: int = 0
    last_mode: GrammarReviewMode | None = None


@dataclass(frozen=True, slots=True)
class GrammarReviewStudentState:
    """Persisted student review snapshot under grammar.review."""

    student_id: int
    language_id: int
    history: tuple[GrammarReviewHistoryEntry, ...] = ()
    schema_version: int = GRAMMAR_REVIEW_SCHEMA_VERSION

    def history_for(self, grammar_id: str) -> GrammarReviewHistoryEntry | None:
        for entry in self.history:
            if entry.grammar_id == grammar_id:
                return entry
        return None


@dataclass(frozen=True, slots=True)
class GrammarReviewItem:
    """Single review queue / schedule entry (G0 name retained)."""

    grammar_id: str
    due_at: str
    priority: GrammarReviewPriority
    reason: GrammarReviewReason
    recommended_review_mode: GrammarReviewMode
    review_due: bool = False
    urgency_score: float = 0.0
    retention_risk: float = 0.0


@dataclass(frozen=True, slots=True)
class GrammarReviewQueue:
    """Deterministic ordered review queue (due / early-pull items only)."""

    items: tuple[GrammarReviewItem, ...] = ()

    def grammar_ids(self) -> tuple[str, ...]:
        return tuple(item.grammar_id for item in self.items)


@dataclass(frozen=True, slots=True)
class GrammarReviewSnapshot:
    """Full review computation: per-topic schedule + due queue."""

    student_id: int
    language_id: int
    as_of: str
    schedule: tuple[GrammarReviewItem, ...] = ()
    queue: GrammarReviewQueue = field(default_factory=GrammarReviewQueue)
    enabled: bool = True
    schema_version: int = GRAMMAR_REVIEW_SCHEMA_VERSION

    def item_for(self, grammar_id: str) -> GrammarReviewItem | None:
        for item in self.schedule:
            if item.grammar_id == grammar_id:
                return item
        return None
