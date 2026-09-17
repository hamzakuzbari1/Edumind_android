"""Transaction boundaries for Grammar Learning Pipeline.

Failures must never partially update mastery / review / progression.
"""

from __future__ import annotations

from dataclasses import replace

from app.services.language_grammar_pipeline.types import WriteGate


def mark_evaluation_succeeded(gate: WriteGate) -> WriteGate:
    return replace(gate, evaluation_succeeded=True)


def mark_evidence_ready(gate: WriteGate) -> WriteGate:
    return replace(gate, evidence_ready=True)


def mark_mastery_applied(gate: WriteGate) -> WriteGate:
    return replace(gate, mastery_applied=True)


def mark_review_applied(gate: WriteGate) -> WriteGate:
    return replace(gate, review_applied=True)


def mark_progression_synced(gate: WriteGate) -> WriteGate:
    return replace(gate, progression_synced=True)


def abort_before_writes(gate: WriteGate, reason: str) -> WriteGate:
    """Hard abort before any learner write — clears write-applied flags."""
    return WriteGate(
        evaluation_succeeded=gate.evaluation_succeeded,
        evidence_ready=gate.evidence_ready,
        mastery_applied=False,
        review_applied=False,
        progression_synced=False,
        aborted=True,
        abort_reason=reason,
    )
