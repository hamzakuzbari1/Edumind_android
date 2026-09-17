"""Confidence and evidence telemetry (Phase 3.2.1)."""

from __future__ import annotations

from app.services.language_listening_confidence.constants import MASTERY_THRESHOLD
from app.services.language_listening_confidence.evidence import missing_evidence, objectives_needing_evidence
from app.services.language_listening_confidence.objectives import _review_due
from app.services.language_listening_confidence.types import ConfidenceState, ConfidenceTelemetry


def compute_confidence_telemetry(state: ConfidenceState) -> ConfidenceTelemetry:
    confidences = [rec.confidence for rec in state.objectives.values()]
    coverages = [rec.coverage_score for rec in state.objectives.values()]
    mastery_scores = [rec.mastery_score for rec in state.objectives.values()]
    mastered = [oid for oid, rec in state.objectives.items() if rec.is_mastered]
    conf_only = [
        oid
        for oid, rec in state.objectives.items()
        if rec.confidence >= MASTERY_THRESHOLD and not rec.is_mastered
    ]
    under = [oid for oid, rec in state.objectives.items() if rec.confidence < 0.55]
    high = [oid for oid, rec in state.objectives.items() if rec.confidence >= MASTERY_THRESHOLD]
    needs_evidence = objectives_needing_evidence(state)

    return ConfidenceTelemetry(
        level=state.level,
        lesson_index=state.lesson_index,
        mastered_count=len(mastered),
        confidence_only_mastered=len(conf_only),
        under_confident=under,
        high_confidence=high,
        needs_evidence=needs_evidence,
        average_confidence=round(sum(confidences) / max(1, len(confidences)), 4),
        average_coverage=round(sum(coverages) / max(1, len(coverages)), 4),
        average_mastery_score=round(sum(mastery_scores) / max(1, len(mastery_scores)), 4),
        total_gain=round(sum(rec.total_gain for rec in state.objectives.values()), 4),
        total_decay=round(sum(rec.total_decay for rec in state.objectives.values()), 4),
        confidence_by_objective={oid: round(rec.confidence, 4) for oid, rec in state.objectives.items()},
        coverage_by_objective={oid: rec.coverage_score for oid, rec in state.objectives.items()},
        mastery_by_objective={oid: rec.mastery_score for oid, rec in state.objectives.items()},
        trends={oid: round(rec.trend, 4) for oid, rec in state.objectives.items() if rec.trend},
        review_due=_review_due(state, state.lesson_index),
        missing_evidence_summary={
            oid: missing_evidence(rec) for oid, rec in state.objectives.items() if oid in needs_evidence
        },
    )
