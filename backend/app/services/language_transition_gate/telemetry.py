"""Transition gate recommendations from real listening telemetry (Phase 5.2)."""

from __future__ import annotations

from app.services.language_transition_gate.rules import (
    REQUIREMENT_CHALLENGE_STABILITY,
    REQUIREMENT_CONFIDENCE,
    REQUIREMENT_EVIDENCE,
    REQUIREMENT_LESSON_EXPOSURE,
    REQUIREMENT_OBJECTIVE_MASTERY,
    REQUIREMENT_RECENT_CONSISTENCY,
    REQUIREMENT_REVIEW_COMPLETION,
    REQUIREMENT_STAGE_SCORE,
)
from app.services.language_transition_gate.types import GateRequirementResult, TransitionGateContext


def build_recommendations(
    *,
    ctx: TransitionGateContext,
    failed: tuple[GateRequirementResult, ...],
) -> tuple[str, ...]:
    """Actionable advice derived from failed requirements and live telemetry."""
    if not failed:
        return ()

    recs: list[str] = []
    failed_names = {req.name for req in failed}

    if REQUIREMENT_EVIDENCE in failed_names:
        if ctx.missing_speaker_evidence:
            recs.append("Practice more multi-speaker lessons to broaden speaker evidence.")
        if ctx.missing_inference_evidence:
            recs.append("Improve inference evidence with inference-focused listening tasks.")
        if ctx.needs_evidence_objectives:
            labels = ", ".join(ctx.needs_evidence_objectives[:3])
            recs.append(f"Close evidence gaps for: {labels}.")
        if REQUIREMENT_EVIDENCE in failed_names and not any(
            r.startswith("Practice") or r.startswith("Improve") or r.startswith("Close")
            for r in recs
        ):
            recs.append(
                f"Raise evidence coverage from {int(ctx.evidence_coverage_avg * 100)}% "
                "with varied format and topic exposure."
            )

    if REQUIREMENT_REVIEW_COMPLETION in failed_names:
        if ctx.review_due_objectives:
            due = ", ".join(ctx.review_due_objectives[:3])
            recs.append(f"Complete pending review lessons for: {due}.")
        elif ctx.pending_review_count:
            recs.append(
                f"Complete {ctx.pending_review_count} pending review lesson(s) before transitioning."
            )
        else:
            recs.append("Complete pending review lessons to strengthen retention.")

    if REQUIREMENT_CONFIDENCE in failed_names:
        recs.append(
            f"Build listening confidence (currently {int(ctx.confidence_avg * 100)}%) "
            "through targeted practice on weaker objectives."
        )

    if REQUIREMENT_RECENT_CONSISTENCY in failed_names:
        recs.append("Increase listening consistency with regular short sessions across recent lessons.")

    if REQUIREMENT_CHALLENGE_STABILITY in failed_names:
        recs.append(
            f"Stabilize challenge performance at Normal level "
            f"(current: {ctx.challenge_level}, demote streak: {ctx.demote_streak})."
        )

    if REQUIREMENT_OBJECTIVE_MASTERY in failed_names:
        remaining = max(0, ctx.total_objectives - ctx.mastered_objectives)
        recs.append(
            f"Master {remaining} more curriculum objective(s) "
            f"({ctx.mastered_objectives}/{ctx.total_objectives} complete)."
        )

    if REQUIREMENT_LESSON_EXPOSURE in failed_names:
        recs.append(
            f"Complete more listening lessons ({ctx.lesson_index} completed; "
            f"minimum exposure not yet met)."
        )

    if REQUIREMENT_STAGE_SCORE in failed_names:
        recs.append(
            f"Raise overall stage score from {ctx.stage_score} through balanced progress "
            "across confidence, evidence, and challenge."
        )

    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for rec in recs:
        if rec not in seen:
            seen.add(rec)
            unique.append(rec)
    return tuple(unique)


def estimate_remaining_progress(
    requirements: tuple[GateRequirementResult, ...],
) -> float:
    """Average progress across all requirements — 100 when all pass."""
    from app.services.language_transition_gate.rules import requirement_progress

    if not requirements:
        return 0.0
    scores = [requirement_progress(req) for req in requirements]
    return round(sum(scores) / len(scores), 1)
