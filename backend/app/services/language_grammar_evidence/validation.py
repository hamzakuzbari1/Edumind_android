"""Validate Grammar Evidence observations against the Catalog (G2.2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_grammar.id_canon import is_canonical_grammar_id, normalize_grammar_id
from app.services.language_grammar_catalog.catalog import all_grammar_ids
from app.services.language_grammar_evidence.types import (
    GrammarEvidenceBatch,
    GrammarEvidenceObservation,
)


class GrammarEvidenceError(ValueError):
    """Malformed or invalid grammar evidence."""


@dataclass
class EvidenceValidationResult:
    valid: bool = True
    issues: list[str] = field(default_factory=list)
    observations: tuple[GrammarEvidenceObservation, ...] = ()

    def add(self, message: str) -> None:
        self.issues.append(message)
        self.valid = False


def _clamp_signal(value: float | None, *, field_name: str, observation_id: str) -> float | None:
    if value is None:
        return None
    if value < 0.0 or value > 100.0:
        raise GrammarEvidenceError(
            f"Impossible {field_name} for {observation_id}: {value}"
        )
    return float(value)


def validate_observation(
    obs: GrammarEvidenceObservation,
    *,
    catalog_ids: frozenset[str] | None = None,
    seen_ids: set[str] | None = None,
) -> GrammarEvidenceObservation:
    """Validate and normalize one observation. Raises GrammarEvidenceError on failure."""
    oid = (obs.observation_id or "").strip()
    if not oid:
        raise GrammarEvidenceError("observation_id is required")
    if seen_ids is not None:
        if oid in seen_ids:
            raise GrammarEvidenceError(f"Duplicate evidence ID: {oid}")
        seen_ids.add(oid)

    gid = normalize_grammar_id(obs.grammar_id)
    if not is_canonical_grammar_id(gid):
        raise GrammarEvidenceError(f"Invalid grammar_id: {obs.grammar_id!r}")
    ids = catalog_ids if catalog_ids is not None else all_grammar_ids()
    if gid not in ids:
        raise GrammarEvidenceError(f"Unknown grammar_id: {gid}")

    if obs.attempt_count < 0 or obs.correct_count < 0:
        raise GrammarEvidenceError(f"Negative attempts/correct for {oid}")
    if obs.correct_count > obs.attempt_count:
        raise GrammarEvidenceError(f"correct_count > attempt_count for {oid}")
    if not (obs.context or "").strip():
        raise GrammarEvidenceError(f"context is required for {oid}")
    if obs.student_id <= 0 or obs.language_id <= 0:
        raise GrammarEvidenceError(f"Invalid student/language for {oid}")
    if obs.confidence is not None and not (0.0 <= obs.confidence <= 1.0):
        raise GrammarEvidenceError(f"confidence must be in [0,1] for {oid}")

    score = obs.score
    if score is not None and not (0.0 <= float(score) <= 100.0):
        raise GrammarEvidenceError(f"score must be in [0,100] for {oid}")

    return GrammarEvidenceObservation(
        observation_id=oid,
        grammar_id=gid,
        context=obs.context.strip(),
        attempt_count=int(obs.attempt_count),
        correct_count=int(obs.correct_count),
        observation_type=obs.observation_type,
        source_skill=obs.source_skill,
        student_id=int(obs.student_id),
        language_id=int(obs.language_id),
        observed_at=obs.observed_at,
        confidence=obs.confidence,
        understanding_signal=_clamp_signal(obs.understanding_signal, field_name="understanding_signal", observation_id=oid),
        accuracy_signal=_clamp_signal(obs.accuracy_signal, field_name="accuracy_signal", observation_id=oid),
        fluency_signal=_clamp_signal(obs.fluency_signal, field_name="fluency_signal", observation_id=oid),
        retention_signal=_clamp_signal(obs.retention_signal, field_name="retention_signal", observation_id=oid),
        activity_id=str(obs.activity_id or "").strip(),
        activity_type=str(obs.activity_type or "").strip(),
        lesson_id=str(obs.lesson_id or "").strip(),
        score=float(score) if score is not None else None,
    )


def validate_batch(batch: GrammarEvidenceBatch) -> EvidenceValidationResult:
    """Validate a batch; returns normalized observations or issues."""
    result = EvidenceValidationResult()
    catalog_ids = all_grammar_ids()
    seen: set[str] = set()
    normalized: list[GrammarEvidenceObservation] = []
    for obs in batch.observations:
        try:
            normalized.append(validate_observation(obs, catalog_ids=catalog_ids, seen_ids=seen))
        except GrammarEvidenceError as exc:
            result.add(str(exc))
    if result.valid:
        result.observations = tuple(normalized)
    return result
