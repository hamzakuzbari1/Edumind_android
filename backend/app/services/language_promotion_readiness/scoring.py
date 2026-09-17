"""Continuous promotion readiness scoring (Phase 5.3).

Readiness is a weighted 0–100 blend — never binary AND logic.
Thresholds for the promotion bar live here and in transition gate rules.
"""

from __future__ import annotations

from app.services.language_learning_stage.types import ListeningLearningStage
from app.services.language_promotion_readiness.types import (
    ReadinessDimensionScore,
    ReadinessStatus,
)
from app.services.language_transition_gate.rules import GATE_THRESHOLDS
from app.services.language_transition_gate.types import TransitionGateContext, TransitionGateResult

# Continuous dimension weights (sum = 1.0).
READINESS_WEIGHTS: dict[str, float] = {
    "learning_stage": 0.12,
    "stage_score": 0.10,
    "transition_gate": 0.18,
    "confidence": 0.12,
    "evidence": 0.12,
    "objective_mastery": 0.10,
    "challenge_stability": 0.08,
    "consistency": 0.08,
    "review_completion": 0.05,
    "lesson_exposure": 0.05,
}

# Educational impact for blocker ranking (higher = more important).
BLOCKER_IMPACT: dict[str, float] = {
    "evidence": 1.00,
    "learning_stage": 0.95,
    "stage_score": 0.90,
    "confidence": 0.85,
    "objective_mastery": 0.80,
    "transition_gate": 0.78,
    "review_completion": 0.72,
    "lesson_exposure": 0.68,
    "challenge_stability": 0.65,
    "consistency": 0.60,
}

STATUS_THRESHOLDS: tuple[tuple[int, ReadinessStatus], ...] = (
    (100, ReadinessStatus.PROMOTION_AVAILABLE),
    (80, ReadinessStatus.READY),
    (50, ReadinessStatus.ALMOST_READY),
    (0, ReadinessStatus.NOT_READY),
)


def promotion_bar_thresholds():
    """Promotion test bar = Advanced stage gate thresholds (Intermediate -> Advanced)."""
    key = (int(ListeningLearningStage.intermediate), int(ListeningLearningStage.advanced))
    return GATE_THRESHOLDS[key]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _ratio_progress(current: float, required: float) -> float:
    if required <= 0:
        return 1.0 if current > 0 else 0.0
    return _clamp01(current / required)


def score_to_status(readiness_score: int) -> ReadinessStatus:
    score = max(0, min(100, int(readiness_score)))
    for threshold, status in STATUS_THRESHOLDS:
        if score >= threshold:
            return status
    return ReadinessStatus.NOT_READY


def compute_dimension_scores(
    *,
    ctx: TransitionGateContext,
    gate: TransitionGateResult,
) -> list[ReadinessDimensionScore]:
    bar = promotion_bar_thresholds()
    stage_progress = (ctx.persistent_stage - 1) / max(1, int(ListeningLearningStage.advanced) - 1)
    gate_progress = gate.overall_gate_score / 100.0

    challenge_ok = (
        ctx.challenge_level.lower() in {"normal", "hard", "exam"}
        and ctx.demote_streak <= bar.max_demote_streak
    )
    challenge_progress = _clamp01(
        _ratio_progress(ctx.challenge_score, bar.min_challenge_score) * (1.0 if challenge_ok else 0.75)
    )

    review_base = _ratio_progress(ctx.review_completion_ratio, bar.min_review_completion)
    if ctx.pending_review_count > 0:
        review_progress = review_base * max(0.0, 1.0 - ctx.pending_review_count * 0.15)
    else:
        review_progress = review_base

    raw_dimensions: list[tuple[str, float, float]] = [
        ("learning_stage", stage_progress, 1.0),
        ("stage_score", ctx.stage_score / 100.0, bar.min_stage_score / 100.0),
        ("transition_gate", gate_progress, 1.0),
        ("confidence", ctx.confidence_avg, bar.min_confidence),
        ("evidence", ctx.evidence_coverage_avg, bar.min_evidence_coverage),
        ("objective_mastery", ctx.objective_mastery_ratio, bar.min_objective_mastery),
        ("challenge_stability", challenge_progress, 1.0),
        ("consistency", ctx.recent_consistency, bar.min_recent_consistency),
        ("review_completion", review_progress, 1.0),
        ("lesson_exposure", float(ctx.lesson_index), float(bar.min_lesson_exposure)),
    ]

    scores: list[ReadinessDimensionScore] = []
    for name, current, required in raw_dimensions:
        if name in {"learning_stage", "transition_gate", "challenge_stability", "review_completion"}:
            progress = _clamp01(current)
        else:
            progress = _ratio_progress(current, required)
        weight = READINESS_WEIGHTS[name]
        scores.append(
            ReadinessDimensionScore(
                name=name,
                current=round(current, 4),
                required=round(required, 4),
                progress=round(progress, 4),
                weight=weight,
                contribution=round(progress * weight * 100.0, 2),
            )
        )
    return scores


def compute_readiness_score(dimensions: list[ReadinessDimensionScore]) -> int:
    total = sum(d.contribution for d in dimensions)
    return int(max(0, min(100, round(total))))


def compute_estimated_remaining(readiness_score: int) -> float:
    return round(max(0.0, 100.0 - readiness_score), 1)


def rank_blocker_gaps(
    dimensions: list[ReadinessDimensionScore],
) -> list[tuple[str, float]]:
    gaps: list[tuple[str, float]] = []
    for dim in dimensions:
        gap = max(0.0, 1.0 - dim.progress)
        if gap <= 0.001:
            continue
        impact = BLOCKER_IMPACT.get(dim.name, 0.5)
        gaps.append((dim.name, gap * impact))
    gaps.sort(key=lambda item: item[1], reverse=True)
    return gaps
