"""Readiness history and rolling statistics (Phase 5.3.1)."""

from __future__ import annotations

from app.services.language_promotion_stability.policy import StabilityPolicy
from app.services.language_promotion_stability.types import ReadinessHistoryEntry, RollingReadinessStats


def append_history_entry(
    history: list[ReadinessHistoryEntry],
    entry: ReadinessHistoryEntry,
    *,
    policy: StabilityPolicy,
) -> list[ReadinessHistoryEntry]:
    """Append or replace entry for the same lesson_index; trim to max length."""
    updated = [e for e in history if e.lesson_index != entry.lesson_index]
    updated.append(entry)
    updated.sort(key=lambda e: e.lesson_index)
    if len(updated) > policy.max_history_entries:
        updated = updated[-policy.max_history_entries :]
    return updated


def windowed_history(
    history: list[ReadinessHistoryEntry],
    *,
    policy: StabilityPolicy,
) -> list[ReadinessHistoryEntry]:
    if not history:
        return []
    return history[-policy.rolling_window :]


def compute_rolling_stats(
    history: list[ReadinessHistoryEntry],
    *,
    policy: StabilityPolicy,
) -> RollingReadinessStats:
    window = windowed_history(history, policy=policy)
    scores = [e.readiness_score for e in window]

    if not scores:
        return RollingReadinessStats(
            last_readiness_scores=(),
            rolling_average=0.0,
            rolling_minimum=0.0,
            rolling_variance=0.0,
            stable_lessons=0,
            best_streak=0,
            current_streak=0,
        )

    avg = sum(scores) / len(scores)
    minimum = min(scores)
    variance = sum((s - avg) ** 2 for s in scores) / len(scores)
    stable = sum(1 for s in scores if s >= policy.stable_lesson_threshold)

    best_streak = 0
    current_streak = 0
    run = 0
    for score in scores:
        if score >= policy.stable_lesson_threshold:
            run += 1
            best_streak = max(best_streak, run)
        else:
            run = 0
    for score in reversed(scores):
        if score >= policy.stable_lesson_threshold:
            current_streak += 1
        else:
            break

    return RollingReadinessStats(
        last_readiness_scores=tuple(scores),
        rolling_average=round(avg, 1),
        rolling_minimum=float(minimum),
        rolling_variance=round(variance, 2),
        stable_lessons=stable,
        best_streak=best_streak,
        current_streak=current_streak,
    )


def smoothed_readiness_score(
    *,
    current_score: int,
    stats: RollingReadinessStats,
    history_length: int,
    policy: StabilityPolicy,
) -> float:
    """Blend current score with rolling average to damp single-lesson spikes."""
    if history_length <= 1:
        weight_current = 0.25
    elif history_length < policy.min_lessons_for_high_confidence:
        weight_current = 0.35
    else:
        weight_current = 0.45

    blended = weight_current * current_score + (1.0 - weight_current) * stats.rolling_average
    if history_length < policy.rolling_window:
        window_factor = history_length / policy.rolling_window
        blended *= 0.55 + 0.45 * window_factor
    return round(min(current_score, blended), 1)


def compute_trend(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return round(values[-1] - values[-2], 4)


def recent_gate_passes(
    history: list[ReadinessHistoryEntry],
    *,
    policy: StabilityPolicy,
) -> tuple[bool, ...]:
    window = windowed_history(history, policy=policy)
    recent = window[-policy.gate_pass_recent_lessons :]
    return tuple(e.gate_eligible for e in recent)


def has_severe_regression(
    history: list[ReadinessHistoryEntry],
    *,
    policy: StabilityPolicy,
) -> tuple[bool, bool]:
    """Return (confidence_regression, evidence_regression) on latest lesson."""
    if len(history) < 2:
        return False, False
    prev = history[-2]
    curr = history[-1]
    conf_drop = prev.confidence_avg - curr.confidence_avg
    evid_drop = prev.evidence_coverage_avg - curr.evidence_coverage_avg
    return (
        conf_drop >= policy.severe_confidence_regression,
        evid_drop >= policy.severe_evidence_regression,
    )
