"""Promotion stability predictions and recommendations (Phase 5.3.1)."""

from __future__ import annotations

from app.services.language_promotion_stability.policy import StabilityPolicy
from app.services.language_promotion_stability.types import (
    PromotionPrediction,
    PromotionStabilityResult,
    ReadinessHistoryEntry,
    RollingReadinessStats,
)
from app.services.language_promotion_readiness.types import PromotionReadinessResult


def build_recommendations(
    *,
    result: PromotionStabilityResult,
    readiness: PromotionReadinessResult,
    history: list[ReadinessHistoryEntry],
    stats: RollingReadinessStats,
    policy: StabilityPolicy,
    pending_review_count: int,
    review_due_objectives: tuple[str, ...],
    missing_speaker_evidence: bool,
    missing_inference_evidence: bool,
    needs_evidence_objectives: tuple[str, ...],
) -> tuple[str, ...]:
    recs: list[str] = []

    if len(history) < policy.rolling_window:
        remaining = policy.rolling_window - len(history)
        recs.append(f"Maintain consistency for {remaining} more lesson(s) to build a stable readiness window.")

    if stats.rolling_average < policy.min_rolling_average:
        recs.append(
            f"Raise rolling readiness average from {stats.rolling_average:.1f} "
            f"to at least {policy.min_rolling_average:.0f}."
        )

    if stats.rolling_minimum < policy.min_rolling_minimum:
        recs.append(
            f"Improve weakest recent lesson score (rolling minimum {stats.rolling_minimum:.0f} "
            f"/ target {policy.min_rolling_minimum:.0f})."
        )

    recent_gates = [e.gate_eligible for e in history[-policy.gate_pass_recent_lessons :]]
    if len(recent_gates) < policy.gate_pass_recent_lessons or not all(recent_gates):
        recs.append(
            f"Pass the transition gate in each of the last {policy.gate_pass_recent_lessons} lessons."
        )

    if pending_review_count > 0:
        if review_due_objectives:
            recs.append(f"Complete pending review for: {', '.join(review_due_objectives[:2])}.")
        else:
            recs.append(f"Complete {pending_review_count} pending review lesson(s).")

    if missing_speaker_evidence:
        recs.append("Practice another multi-speaker listening lesson to diversify evidence.")

    if missing_inference_evidence:
        recs.append("Improve announcement and inference evidence coverage.")

    if needs_evidence_objectives and not missing_speaker_evidence and not missing_inference_evidence:
        recs.append(f"Increase evidence diversity for: {', '.join(needs_evidence_objectives[:2])}.")

    if result.prediction in {PromotionPrediction.VERY_LIKELY, PromotionPrediction.LIKELY}:
        recs.append("Continue maintaining current performance across upcoming lessons.")

    if readiness.next_actions:
        for action in readiness.next_actions[:2]:
            if action not in recs:
                recs.append(action)

    seen: set[str] = set()
    unique: list[str] = []
    for rec in recs:
        if rec not in seen:
            seen.add(rec)
            unique.append(rec)
    return tuple(unique[:6])


def primary_recommendation(recommendations: tuple[str, ...], prediction: PromotionPrediction) -> str:
    if recommendations:
        return recommendations[0]
    mapping = {
        PromotionPrediction.VERY_LIKELY: "Continue maintaining current performance across upcoming lessons.",
        PromotionPrediction.LIKELY: "Keep building stable readiness over the next few lessons.",
        PromotionPrediction.BORDERLINE: "Address primary blockers before expecting promotion test availability.",
        PromotionPrediction.UNCERTAIN: "Focus on consistency before promotion readiness can stabilize.",
        PromotionPrediction.NOT_READY: "Build lesson history and close evidence gaps before promotion planning.",
    }
    return mapping[prediction]
