"""Listening Promotion Readiness Engine (Phase 5.3).

Official CEFR -> Learning Stage -> Transition Gate -> Promotion Readiness -> Promotion Test (future).

Readiness is continuous (0-100). It never promotes or changes Official CEFR.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_learning_stage.scoring import compute_signal_contributions, compute_stage_score
from app.services.language_learning_stage.signals import gather_listening_signals
from app.services.language_learning_stage.storage import load_listening_stage
from app.services.language_progression_service import get_official_cefr
from app.services.language_promotion_readiness.scoring import (
    compute_dimension_scores,
    compute_estimated_remaining,
    compute_readiness_score,
    rank_blocker_gaps,
    score_to_status,
)
from app.services.language_promotion_readiness.storage import save_listening_promotion_readiness
from app.services.language_promotion_readiness.telemetry import (
    build_blockers,
    build_next_actions,
    build_strengths,
)
from app.services.language_promotion_readiness.types import (
    PromotionReadinessResult,
    PromotionReadinessTelemetry,
)
from app.services.language_transition_gate.engine import build_gate_context, evaluate_transition_gate


def evaluate_promotion_readiness(
    *,
    ctx,
    gate,
) -> PromotionReadinessResult:
    """Pure evaluation from transition gate context and gate result."""
    dimensions = compute_dimension_scores(ctx=ctx, gate=gate)
    readiness_score = compute_readiness_score(dimensions)
    status = score_to_status(readiness_score)
    ranked = rank_blocker_gaps(dimensions)
    primary, secondary = build_blockers(dimensions=dimensions, ranked_gaps=ranked)
    strengths = build_strengths(ctx=ctx, dimensions=dimensions)
    next_actions = build_next_actions(ctx=ctx, dimensions=dimensions, ranked_gaps=ranked)

    telemetry = PromotionReadinessTelemetry(
        official_cefr=ctx.official_cefr,
        persistent_stage=ctx.persistent_stage,
        stage_score=ctx.stage_score,
        gate_overall_score=gate.overall_gate_score,
        gate_eligible=gate.eligible,
        dimension_scores=tuple(dimensions),
    )

    return PromotionReadinessResult(
        official_cefr=ctx.official_cefr,
        readiness_score=readiness_score,
        status=status,
        estimated_remaining=compute_estimated_remaining(readiness_score),
        primary_blockers=primary,
        secondary_blockers=secondary,
        strengths=strengths,
        next_actions=next_actions,
        telemetry=telemetry,
    )


async def evaluate_listening_promotion_readiness(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
) -> PromotionReadinessResult:
    """Compute listening promotion readiness — does not promote or change CEFR."""
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
    gate = evaluate_transition_gate(ctx)
    return evaluate_promotion_readiness(ctx=ctx, gate=gate)


async def evaluate_and_persist_listening_promotion_readiness(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
) -> PromotionReadinessResult:
    """Evaluate and persist readiness telemetry — never promotes."""
    result = await evaluate_listening_promotion_readiness(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=official_cefr,
    )
    await save_listening_promotion_readiness(
        db,
        student_id=student_id,
        language_id=language_id,
        result=result,
    )
    return result
