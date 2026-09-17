"""Promotion stability scoring helpers (Phase 5.3.1)."""

from __future__ import annotations

from app.services.language_promotion_stability.history import (
    has_severe_regression,
    recent_gate_passes,
    smoothed_readiness_score,
)
from app.services.language_promotion_stability.policy import StabilityPolicy
from app.services.language_promotion_stability.types import (
    PromotionPrediction,
    ReadinessHistoryEntry,
    RollingReadinessStats,
)
from app.services.language_promotion_readiness.types import PromotionReadinessResult


def _clamp100(value: float) -> int:
    return int(max(0, min(100, round(value))))


def compute_readiness_stability(
    *,
    stats: RollingReadinessStats,
    history: list[ReadinessHistoryEntry],
    readiness: PromotionReadinessResult,
    policy: StabilityPolicy,
) -> float:
    """0–100 stability score from rolling policy adherence."""
    if not history:
        return 0.0

    avg_ratio = min(1.0, stats.rolling_average / policy.min_rolling_average)
    min_ratio = min(1.0, stats.rolling_minimum / policy.min_rolling_minimum)

    gate_recent = recent_gate_passes(history, policy=policy)
    gate_ratio = (
        sum(1 for passed in gate_recent if passed) / len(gate_recent) if gate_recent else 0.0
    )
    if len(gate_recent) < policy.gate_pass_recent_lessons:
        gate_ratio *= len(gate_recent) / policy.gate_pass_recent_lessons

    conf_reg, evid_reg = has_severe_regression(history, policy=policy)
    regression_penalty = 0.15 if conf_reg else 0.0
    regression_penalty += 0.15 if evid_reg else 0.0

    variance_penalty = min(0.2, stats.rolling_variance / 200.0)
    history_factor = min(1.0, len(history) / policy.rolling_window)

    raw = (
        0.30 * avg_ratio
        + 0.25 * min_ratio
        + 0.25 * gate_ratio
        + 0.10 * (stats.current_streak / max(1, policy.gate_pass_recent_lessons))
        + 0.10 * history_factor
    )
    stability = max(0.0, raw - regression_penalty - variance_penalty) * 100.0

    if readiness.readiness_score >= 100 and len(history) < policy.min_lessons_for_high_confidence:
        stability = min(stability, policy.short_history_confidence_cap)

    return round(stability, 1)


def compute_promotion_confidence(
    *,
    stats: RollingReadinessStats,
    history: list[ReadinessHistoryEntry],
    readiness: PromotionReadinessResult,
    stability_score: float,
    smoothed: float,
    confidence_trend: float,
    evidence_trend: float,
    review_trend: float,
    consistency_trend: float,
    challenge_score: float,
    policy: StabilityPolicy,
) -> int:
    gate_recent = recent_gate_passes(history, policy=policy)
    gate_consistency = (
        sum(1 for passed in gate_recent if passed) / len(gate_recent) if gate_recent else 0.0
    )

    trend_signal = (
        0.30 * min(1.0, max(0.0, 0.5 + confidence_trend))
        + 0.30 * min(1.0, max(0.0, 0.5 + evidence_trend))
        + 0.20 * min(1.0, max(0.0, 0.5 + review_trend))
        + 0.20 * min(1.0, max(0.0, 0.5 + consistency_trend))
    )

    raw = (
        policy.weight_stability * (stability_score / 100.0)
        + policy.weight_smoothed_readiness * (smoothed / 100.0)
        + policy.weight_gate_consistency * gate_consistency
        + policy.weight_trends * trend_signal
        + policy.weight_challenge * min(1.0, challenge_score)
    ) * 100.0

    confidence = _clamp100(raw)

    if len(history) <= 1:
        confidence = min(confidence, _clamp100(policy.single_lesson_confidence_cap))
    elif len(history) < policy.min_lessons_for_high_confidence:
        confidence = min(confidence, _clamp100(policy.short_history_confidence_cap))

    if stats.rolling_average < policy.min_rolling_average:
        confidence = min(confidence, _clamp100(stats.rolling_average))

    if stats.rolling_minimum < policy.min_rolling_minimum:
        confidence = min(confidence, _clamp100(stats.rolling_minimum + 5))

    if len(gate_recent) < policy.gate_pass_recent_lessons or not all(gate_recent):
        confidence = min(confidence, 85)

    conf_reg, evid_reg = has_severe_regression(history, policy=policy)
    if conf_reg or evid_reg:
        confidence = min(confidence, 70)

    return confidence


def confidence_to_prediction(confidence: int) -> PromotionPrediction:
    if confidence >= 90:
        return PromotionPrediction.VERY_LIKELY
    if confidence >= 75:
        return PromotionPrediction.LIKELY
    if confidence >= 60:
        return PromotionPrediction.BORDERLINE
    if confidence >= 40:
        return PromotionPrediction.UNCERTAIN
    return PromotionPrediction.NOT_READY
