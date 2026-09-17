"""Challenge scoring and plan alignment (Phase 3.3)."""

from __future__ import annotations

from app.services.language_listening_challenge.constants import (
    CHALLENGE_INFLUENCE,
    CHALLENGE_LEVEL_ORDER,
)
from app.services.language_listening_challenge.types import (
    ChallengeLessonRecord,
    ChallengeLevel,
    ChallengeState,
)
from app.services.language_listening_confidence.types import ConfidenceState


def map_challenge_to_difficulty_band(challenge: ChallengeLevel) -> str:
    mapping = {
        ChallengeLevel.easy: "easy",
        ChallengeLevel.normal: "normal",
        ChallengeLevel.hard: "challenging",
        ChallengeLevel.exam: "challenging",
    }
    return mapping[challenge]


def _band_distance(plan_band: str, target_band: str) -> int:
    order = ("easy", "normal", "challenging")
    try:
        return abs(order.index(plan_band) - order.index(target_band))
    except ValueError:
        return 2


def plan_challenge_match_score(plan, target: ChallengeLevel) -> float:
    """How well an intelligence plan matches the learner's adaptive challenge band."""
    target_band = map_challenge_to_difficulty_band(target)
    plan_band = plan.difficulty_band.value
    dist = _band_distance(plan_band, target_band)
    band_score = {0: 1.0, 1: 0.62, 2: 0.28}.get(dist, 0.28)

    pace = plan.pace.value
    if target == ChallengeLevel.easy:
        pace_score = 1.0 if pace in {"slow_clear", "conversational"} else 0.55
    elif target == ChallengeLevel.normal:
        pace_score = 1.0 if pace in {"conversational", "brisk"} else 0.7
    elif target == ChallengeLevel.hard:
        pace_score = 1.0 if pace in {"brisk", "rapid"} else 0.65
    else:
        pace_score = 1.0 if pace in {"brisk", "rapid"} else 0.6

    inference_bonus = 0.0
    if target in {ChallengeLevel.hard, ChallengeLevel.exam}:
        if plan.quality_spec and getattr(plan.quality_spec, "inference_density", None):
            inference_bonus = 0.08

    return round(min(1.0, 0.72 * band_score + 0.28 * pace_score + inference_bonus), 4)


def blend_with_challenge(
    base_blended: float,
    challenge_match: float,
    *,
    challenge_influence: float = CHALLENGE_INFLUENCE,
) -> tuple[float, float]:
    ch_w = max(0.05, min(0.10, challenge_influence))
    blended = (1.0 - ch_w) * base_blended + ch_w * challenge_match
    return round(blended, 4), ch_w


def compute_lesson_performance_score(
    *,
    accuracy: float,
    passed: bool,
    confidence_trend: float,
    evidence_growth: float,
    review_performance: float,
    was_review: bool,
    success_streak: int,
    failure_streak: int,
    time_spent_sec: float | None = None,
    hint_count: int = 0,
    retry_count: int = 0,
) -> float:
    acc = max(0.0, min(1.0, accuracy))
    trend = max(-0.15, min(0.15, confidence_trend))
    trend_norm = (trend + 0.15) / 0.30
    evidence = max(0.0, min(0.25, evidence_growth)) / 0.25
    review = review_performance if was_review else acc
    streak = 0.5
    if success_streak >= 3:
        streak = min(1.0, 0.55 + success_streak * 0.08)
    elif failure_streak >= 2:
        streak = max(0.0, 0.45 - failure_streak * 0.1)

    if time_spent_sec is None:
        time_factor = 0.5
    else:
        time_factor = 0.65 if 90 <= time_spent_sec <= 420 else 0.45

    hint_penalty = max(0.0, 1.0 - hint_count * 0.12)
    retry_penalty = 1.0 if retry_count <= 1 else max(0.35, 1.0 - (retry_count - 1) * 0.18)
    pass_bonus = 0.04 if passed else -0.06

    raw = (
        0.28 * acc
        + 0.18 * trend_norm
        + 0.14 * evidence
        + 0.10 * review
        + 0.12 * streak
        + 0.06 * time_factor
        + 0.06 * hint_penalty
        + 0.06 * retry_penalty
        + pass_bonus
    )
    return round(max(0.0, min(1.0, raw)), 4)


def compute_challenge_score(
    state: ChallengeState,
    confidence_state: ConfidenceState | None = None,
) -> float:
    window = state.history[-15:]
    if not window:
        if confidence_state is not None:
            trends = [rec.trend for rec in confidence_state.objectives.values()]
            avg_trend = sum(trends) / max(1, len(trends))
            return round(0.5 + avg_trend * 0.8, 4)
        return 0.5

    lesson_scores = [rec.lesson_score for rec in window]
    base = sum(lesson_scores) / len(lesson_scores)

    if confidence_state is not None:
        trends = [rec.trend for rec in confidence_state.objectives.values()]
        avg_trend = sum(trends) / max(1, len(trends))
        base = 0.88 * base + 0.12 * ((avg_trend + 0.15) / 0.30)

    recent = window[-5:]
    recent_avg = sum(rec.lesson_score for rec in recent) / len(recent)
    return round(0.72 * base + 0.28 * recent_avg, 4)


def next_challenge_level(current: ChallengeLevel) -> ChallengeLevel | None:
    order = [ChallengeLevel(v) for v in CHALLENGE_LEVEL_ORDER]
    idx = order.index(current)
    if idx >= len(order) - 1:
        return None
    return order[idx + 1]


def prev_challenge_level(current: ChallengeLevel) -> ChallengeLevel | None:
    order = [ChallengeLevel(v) for v in CHALLENGE_LEVEL_ORDER]
    idx = order.index(current)
    if idx <= 0:
        return None
    return order[idx - 1]
