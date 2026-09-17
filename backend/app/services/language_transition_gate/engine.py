"""Listening Transition Gate Engine (Phase 5.2)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_learning_stage.scoring import compute_signal_contributions, compute_stage_score
from app.services.language_learning_stage.signals import gather_listening_signals
from app.services.language_learning_stage.storage import load_listening_stage
from app.services.language_progression_service import get_official_cefr
from app.services.language_transition_gate.rules import (
    evaluate_all_requirements,
    requirement_progress,
    thresholds_for_stage,
)
from app.services.language_transition_gate.telemetry import (
    build_recommendations,
    estimate_remaining_progress,
)
from app.services.language_transition_gate.types import TransitionGateContext, TransitionGateResult


def build_gate_context(
    *,
    official_cefr: str,
    persistent_stage: int,
    stage_score: int,
    snapshot,
    challenge_level: str,
    demote_streak: int,
    pending_review_count: int,
    review_due_objectives: tuple[str, ...],
    needs_evidence_objectives: tuple[str, ...],
    missing_speaker_evidence: bool,
    missing_inference_evidence: bool,
) -> TransitionGateContext:
    return TransitionGateContext(
        official_cefr=official_cefr.upper(),
        persistent_stage=persistent_stage,
        stage_score=stage_score,
        confidence_avg=snapshot.confidence_avg,
        evidence_coverage_avg=snapshot.evidence_coverage_avg,
        objective_mastery_ratio=snapshot.objective_mastery_ratio,
        challenge_score=snapshot.challenge_score,
        challenge_level=challenge_level,
        demote_streak=demote_streak,
        review_completion_ratio=snapshot.review_completion_ratio,
        pending_review_count=pending_review_count,
        recent_consistency=snapshot.recent_stability,
        lesson_index=snapshot.lesson_index,
        mastered_objectives=snapshot.mastered_objectives,
        total_objectives=snapshot.total_objectives,
        needs_evidence_objectives=needs_evidence_objectives,
        review_due_objectives=review_due_objectives,
        missing_speaker_evidence=missing_speaker_evidence,
        missing_inference_evidence=missing_inference_evidence,
    )


def evaluate_transition_gate(ctx: TransitionGateContext) -> TransitionGateResult:
    """Pure gate evaluation — AND logic across all listening requirements."""
    resolved = thresholds_for_stage(ctx.persistent_stage)
    if resolved is None:
        return TransitionGateResult(
            eligible=False,
            overall_gate_score=100.0,
            requirements=(),
            passed_requirements=(),
            failed_requirements=(),
            recommendations=(),
            estimated_remaining_progress=100.0,
            primary_blocker="Already at Advanced — no further learning stage within this CEFR level.",
            next_stage=None,
            official_cefr=ctx.official_cefr,
            persistent_stage=ctx.persistent_stage,
        )

    next_stage, thresholds = resolved
    requirements = evaluate_all_requirements(ctx, thresholds)
    passed = tuple(req.name for req in requirements if req.passed)
    failed_reqs = tuple(req for req in requirements if not req.passed)
    failed = tuple(req.name for req in failed_reqs)
    eligible = len(failed) == 0

    progress_scores = [requirement_progress(req) for req in requirements]
    overall = round(sum(progress_scores) / len(progress_scores), 1) if progress_scores else 0.0
    remaining = 100.0 if eligible else estimate_remaining_progress(requirements)
    recommendations = build_recommendations(ctx=ctx, failed=failed_reqs)
    primary = failed_reqs[0].message if failed_reqs else None

    return TransitionGateResult(
        eligible=eligible,
        overall_gate_score=overall,
        requirements=requirements,
        passed_requirements=passed,
        failed_requirements=failed,
        recommendations=recommendations,
        estimated_remaining_progress=remaining,
        primary_blocker=primary,
        next_stage=next_stage,
        official_cefr=ctx.official_cefr,
        persistent_stage=ctx.persistent_stage,
    )


async def evaluate_listening_transition_gate(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
) -> TransitionGateResult:
    """Evaluate the listening transition gate from live learner state."""
    if official_cefr is None:
        official_read = await get_official_cefr(
            db, student_id=student_id, language_id=language_id, skill="listening"
        )
        official_cefr = official_read.level.value

    level = official_cefr.upper()
    persistent_stage = await load_listening_stage(db, student_id=student_id, language_id=language_id)
    snapshot = await gather_listening_signals(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=level,
    )
    contributions = compute_signal_contributions(snapshot)
    stage_score = compute_stage_score(contributions)

    ctx = build_gate_context(
        official_cefr=level,
        persistent_stage=persistent_stage,
        stage_score=stage_score,
        snapshot=snapshot,
        challenge_level=snapshot.challenge_level,
        demote_streak=snapshot.demote_streak,
        pending_review_count=snapshot.pending_review_count,
        review_due_objectives=snapshot.review_due_objectives,
        needs_evidence_objectives=snapshot.needs_evidence_objectives,
        missing_speaker_evidence=snapshot.missing_speaker_evidence,
        missing_inference_evidence=snapshot.missing_inference_evidence,
    )
    return evaluate_transition_gate(ctx)


def gate_to_eligibility_conditions(gate: TransitionGateResult) -> tuple[str, ...]:
    """Map gate output to learning-stage transition requirement strings."""
    if gate.next_stage is None:
        return ("persistent_stage=advanced",)
    conditions = [f"persistent_stage={gate.persistent_stage}", f"next_stage={gate.next_stage}"]
    for req in gate.requirements:
        status = "pass" if req.passed else "fail"
        conditions.append(f"{req.name}={status}({req.current}/{req.required})")
    conditions.append("explicit_transition_required")
    return tuple(conditions)
