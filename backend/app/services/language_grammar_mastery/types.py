"""Grammar Mastery types (G2.2) — internal dimensions + public overall-only view."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_grammar.enums import (
    GrammarEvidenceSourceSkill,
    GrammarMasteryState,
    GrammarReinforcementSkill,
)
from app.services.language_grammar_mastery.policy import derive_overall_via_policy

GRAMMAR_MASTERY_SCHEMA_VERSION = 1
APPLIED_OBSERVATION_INDEX_CAP = 512

EMA_BASE_ALPHA = 0.18


@dataclass(frozen=True, slots=True)
class GrammarMasteryDimensions:
    """Internal pedagogical dimensions — not the default student/parent surface.

    ``overall_mastery`` is always derived — never manually assigned by callers.
    """

    understanding: float = 0.0
    accuracy: float = 0.0
    fluency: float = 0.0
    retention: float = 0.0
    overall_mastery: float = 0.0


@dataclass(frozen=True, slots=True)
class GrammarMasteryRecord:
    """Per-student × language × grammar_id mastery state (internal store shape)."""

    student_id: int
    language_id: int
    grammar_id: str
    state: GrammarMasteryState
    dimensions: GrammarMasteryDimensions
    confidence: float = 0.0
    stability: float = 0.0
    retention_risk: float = 0.0
    evidence_count: int = 0
    distinct_context_count: int = 0
    skill_coverage: frozenset[GrammarReinforcementSkill | GrammarEvidenceSourceSkill] = field(
        default_factory=frozenset
    )
    best_score_by_skill: dict[str, float] = field(default_factory=dict)
    best_attempt_count_by_skill: dict[str, int] = field(default_factory=dict)
    best_correct_count_by_skill: dict[str, int] = field(default_factory=dict)
    introduced_at: str | None = None
    last_seen_at: str | None = None
    last_updated_at: str | None = None
    last_mastered_at: str | None = None


@dataclass(frozen=True, slots=True)
class PublicGrammarMasteryView:
    """Public surface — overall mastery only (no internal dimension leak)."""

    grammar_id: str
    overall_mastery: float
    state: GrammarMasteryState
    evidence_count: int = 0
    distinct_context_count: int = 0
    last_seen_at: str | None = None
    last_mastered_at: str | None = None


@dataclass(frozen=True, slots=True)
class GrammarMasterySnapshot:
    """Student mastery bag — reproducible from applied evidence + catalog thresholds."""

    student_id: int
    language_id: int
    records: tuple[GrammarMasteryRecord, ...] = ()
    applied_observation_ids: frozenset[str] = frozenset()
    contexts_by_grammar_id: dict[str, frozenset[str]] = field(default_factory=dict)
    schema_version: int = GRAMMAR_MASTERY_SCHEMA_VERSION
    enabled: bool = True

    def record_for(self, grammar_id: str) -> GrammarMasteryRecord | None:
        for rec in self.records:
            if rec.grammar_id == grammar_id:
                return rec
        return None


def derive_overall_mastery(
    *,
    understanding: float,
    accuracy: float,
    fluency: float,
    retention: float,
    confidence: float = 0.0,
) -> float:
    """Derive overall_mastery via the active MasteryScoringPolicy.

    Call signature is stable; weighting lives only in the policy layer.
    """
    return derive_overall_via_policy(
        understanding=understanding,
        accuracy=accuracy,
        fluency=fluency,
        retention=retention,
        confidence=confidence,
    )


def to_public_view(record: GrammarMasteryRecord) -> PublicGrammarMasteryView:
    """Project internal record to the public overall-only view."""
    return PublicGrammarMasteryView(
        grammar_id=record.grammar_id,
        overall_mastery=float(record.dimensions.overall_mastery),
        state=record.state,
        evidence_count=int(record.evidence_count),
        distinct_context_count=int(record.distinct_context_count),
        last_seen_at=record.last_seen_at,
        last_mastered_at=record.last_mastered_at,
    )


def build_dimensions(
    *,
    understanding: float,
    accuracy: float,
    fluency: float,
    retention: float,
    confidence: float = 0.0,
) -> GrammarMasteryDimensions:
    """Construct dimensions with derived overall (never caller-supplied overall)."""
    return GrammarMasteryDimensions(
        understanding=max(0.0, min(100.0, understanding)),
        accuracy=max(0.0, min(100.0, accuracy)),
        fluency=max(0.0, min(100.0, fluency)),
        retention=max(0.0, min(100.0, retention)),
        overall_mastery=derive_overall_mastery(
            understanding=understanding,
            accuracy=accuracy,
            fluency=fluency,
            retention=retention,
            confidence=confidence,
        ),
    )
