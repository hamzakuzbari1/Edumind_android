"""Listening Promotion Stability Engine (Phase 5.3.1).

Promotion Readiness -> Readiness Stability -> Promotion Confidence -> Promotion Test (future).

Does not modify Learning Stage, Transition Gate, or Promotion Readiness scoring.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_learning_stage.signals import gather_listening_signals
from app.services.language_promotion_readiness.engine import evaluate_listening_promotion_readiness
from app.services.language_promotion_stability.history import (
    append_history_entry,
    compute_rolling_stats,
    compute_trend,
    smoothed_readiness_score,
    windowed_history,
)
from app.services.language_promotion_stability.policy import DEFAULT_STABILITY_POLICY, StabilityPolicy
from app.services.language_promotion_stability.scoring import (
    compute_promotion_confidence,
    compute_readiness_stability,
    confidence_to_prediction,
)
from app.services.language_promotion_stability.storage import (
    load_readiness_history,
    save_listening_promotion_stability,
)
from app.services.language_promotion_stability.telemetry import (
    build_recommendations,
    primary_recommendation,
)
from app.services.language_promotion_stability.types import (
    PromotionStabilityResult,
    PromotionStabilityTelemetry,
    ReadinessHistoryEntry,
)


def build_history_entry(
    *,
    lesson_index: int,
    readiness,
    snapshot,
) -> ReadinessHistoryEntry:
    return ReadinessHistoryEntry(
        lesson_index=lesson_index,
        readiness_score=readiness.readiness_score,
        gate_eligible=readiness.telemetry.gate_eligible,
        confidence_avg=snapshot.confidence_avg,
        evidence_coverage_avg=snapshot.evidence_coverage_avg,
        review_completion_ratio=snapshot.review_completion_ratio,
        recent_consistency=snapshot.recent_stability,
        challenge_score=snapshot.challenge_score,
    )


def evaluate_promotion_stability(
    *,
    readiness,
    snapshot,
    history: list[ReadinessHistoryEntry],
    policy: StabilityPolicy = DEFAULT_STABILITY_POLICY,
) -> tuple[PromotionStabilityResult, list[ReadinessHistoryEntry]]:
    """Pure stability evaluation from readiness result and history."""
    entry = build_history_entry(
        lesson_index=snapshot.lesson_index,
        readiness=readiness,
        snapshot=snapshot,
    )
    updated_history = append_history_entry(history, entry, policy=policy)
    stats = compute_rolling_stats(updated_history, policy=policy)
    smoothed = smoothed_readiness_score(
        current_score=readiness.readiness_score,
        stats=stats,
        history_length=len(updated_history),
        policy=policy,
    )

    window = windowed_history(updated_history, policy=policy)
    confidence_trend = compute_trend([e.confidence_avg for e in window])
    evidence_trend = compute_trend([e.evidence_coverage_avg for e in window])
    review_trend = compute_trend([e.review_completion_ratio for e in window])
    consistency_trend = compute_trend([e.recent_consistency for e in window])

    stability_score = compute_readiness_stability(
        stats=stats,
        history=updated_history,
        readiness=readiness,
        policy=policy,
    )
    confidence = compute_promotion_confidence(
        stats=stats,
        history=updated_history,
        readiness=readiness,
        stability_score=stability_score,
        smoothed=smoothed,
        confidence_trend=confidence_trend,
        evidence_trend=evidence_trend,
        review_trend=review_trend,
        consistency_trend=consistency_trend,
        challenge_score=snapshot.challenge_score,
        policy=policy,
    )
    prediction = confidence_to_prediction(confidence)

    telemetry = PromotionStabilityTelemetry(
        official_cefr=readiness.official_cefr,
        current_readiness_score=readiness.readiness_score,
        smoothed_readiness=smoothed,
        history_length=len(updated_history),
        gate_pass_recent=tuple(
            e.gate_eligible for e in updated_history[-policy.gate_pass_recent_lessons :]
        ),
        confidence_trend=confidence_trend,
        evidence_trend=evidence_trend,
        review_trend=review_trend,
        consistency_trend=consistency_trend,
    )

    interim = PromotionStabilityResult(
        official_cefr=readiness.official_cefr,
        promotion_confidence=confidence,
        readiness_stability=stability_score,
        rolling_average=stats.rolling_average,
        rolling_minimum=stats.rolling_minimum,
        rolling_variance=stats.rolling_variance,
        current_streak=stats.current_streak,
        best_streak=stats.best_streak,
        stable_lessons=stats.stable_lessons,
        last_readiness_scores=stats.last_readiness_scores,
        prediction=prediction,
        recommendation="",
        recommendations=(),
        telemetry=telemetry,
    )

    recommendations = build_recommendations(
        result=interim,
        readiness=readiness,
        history=updated_history,
        stats=stats,
        policy=policy,
        pending_review_count=snapshot.pending_review_count,
        review_due_objectives=snapshot.review_due_objectives,
        missing_speaker_evidence=snapshot.missing_speaker_evidence,
        missing_inference_evidence=snapshot.missing_inference_evidence,
        needs_evidence_objectives=snapshot.needs_evidence_objectives,
    )

    return PromotionStabilityResult(
        official_cefr=interim.official_cefr,
        promotion_confidence=interim.promotion_confidence,
        readiness_stability=interim.readiness_stability,
        rolling_average=interim.rolling_average,
        rolling_minimum=interim.rolling_minimum,
        rolling_variance=interim.rolling_variance,
        current_streak=interim.current_streak,
        best_streak=interim.best_streak,
        stable_lessons=interim.stable_lessons,
        last_readiness_scores=interim.last_readiness_scores,
        prediction=interim.prediction,
        recommendation=primary_recommendation(recommendations, prediction),
        recommendations=recommendations,
        telemetry=interim.telemetry,
    ), updated_history


async def evaluate_listening_promotion_stability(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
    policy: StabilityPolicy = DEFAULT_STABILITY_POLICY,
) -> PromotionStabilityResult:
    """Evaluate promotion confidence without mutating readiness, stage, or gate."""
    readiness = await evaluate_listening_promotion_readiness(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=official_cefr,
    )
    snapshot = await gather_listening_signals(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=readiness.official_cefr,
    )
    history = await load_readiness_history(db, student_id=student_id, language_id=language_id)
    result, _ = evaluate_promotion_stability(
        readiness=readiness,
        snapshot=snapshot,
        history=history,
        policy=policy,
    )
    return result


async def evaluate_and_persist_listening_promotion_stability(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
    policy: StabilityPolicy = DEFAULT_STABILITY_POLICY,
) -> PromotionStabilityResult:
    """Evaluate, update history, and persist stability telemetry."""
    readiness = await evaluate_listening_promotion_readiness(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=official_cefr,
    )
    snapshot = await gather_listening_signals(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=readiness.official_cefr,
    )
    history = await load_readiness_history(db, student_id=student_id, language_id=language_id)
    result, updated_history = evaluate_promotion_stability(
        readiness=readiness,
        snapshot=snapshot,
        history=history,
        policy=policy,
    )
    await save_listening_promotion_stability(
        db,
        student_id=student_id,
        language_id=language_id,
        result=result,
        history=updated_history,
    )
    return result
