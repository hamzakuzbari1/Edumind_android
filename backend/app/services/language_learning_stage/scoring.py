"""Weighted stage scoring for listening learning stages (Phase 5.1 / 5.1.1).

Stage score is a live metric (0–100). Score bands describe performance bands;
they do NOT mutate the persistent learning stage without an explicit transition.
"""

from __future__ import annotations

from app.services.language_learning_stage.types import (
    ListeningLearningStage,
    ListeningSignalSnapshot,
    SignalContribution,
    StageTransitionEligibility,
    STAGE_DISPLAY_NAMES,
)

# Listening-only signal weights (sum = 1.0).
SIGNAL_WEIGHTS: dict[str, float] = {
    "confidence": 0.20,
    "evidence": 0.15,
    "challenge": 0.15,
    "curriculum": 0.15,
    "objective_mastery": 0.15,
    "review_completion": 0.10,
    "recent_stability": 0.10,
}

# Live score bands (metric only — not the persistent stage).
STAGE_SCORE_BANDS: dict[ListeningLearningStage, tuple[int, int]] = {
    ListeningLearningStage.beginner: (0, 39),
    ListeningLearningStage.intermediate: (40, 79),
    ListeningLearningStage.advanced: (80, 100),
}

# Minimum score to be eligible for explicit transition to the next persistent stage.
NEXT_STAGE_MIN_SCORE: dict[ListeningLearningStage, int | None] = {
    ListeningLearningStage.beginner: 40,
    ListeningLearningStage.intermediate: 80,
    ListeningLearningStage.advanced: None,
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def normalize_signal_values(snapshot: ListeningSignalSnapshot) -> dict[str, float]:
    """Map raw snapshot fields to normalized 0..1 scores per signal."""
    return {
        "confidence": _clamp01(snapshot.confidence_avg),
        "evidence": _clamp01(
            0.55 * snapshot.evidence_coverage_avg + 0.45 * snapshot.confidence_mastery_avg
        ),
        "challenge": _clamp01(snapshot.challenge_score),
        "curriculum": _clamp01(snapshot.curriculum_progression),
        "objective_mastery": _clamp01(snapshot.objective_mastery_ratio),
        "review_completion": _clamp01(snapshot.review_completion_ratio),
        "recent_stability": _clamp01(snapshot.recent_stability),
    }


def compute_signal_contributions(snapshot: ListeningSignalSnapshot) -> list[SignalContribution]:
    """Weighted blend → contributions that sum to stage_score (0–100)."""
    normalized = normalize_signal_values(snapshot)
    weight_sum = sum(SIGNAL_WEIGHTS.values())
    if abs(weight_sum - 1.0) > 1e-6:
        raise ValueError(f"SIGNAL_WEIGHTS must sum to 1.0, got {weight_sum}")

    contributions: list[SignalContribution] = []
    for name, weight in SIGNAL_WEIGHTS.items():
        norm = normalized[name]
        contributions.append(
            SignalContribution(
                signal=name,
                raw_value=_raw_for_signal(snapshot, name),
                normalized=round(norm, 4),
                weight=weight,
                contribution=round(norm * weight * 100.0, 2),
            )
        )
    return contributions


def _raw_for_signal(snapshot: ListeningSignalSnapshot, name: str) -> float:
    mapping = {
        "confidence": snapshot.confidence_avg,
        "evidence": snapshot.evidence_coverage_avg,
        "challenge": snapshot.challenge_score,
        "curriculum": snapshot.curriculum_progression,
        "objective_mastery": snapshot.objective_mastery_ratio,
        "review_completion": snapshot.review_completion_ratio,
        "recent_stability": snapshot.recent_stability,
    }
    return float(mapping.get(name, 0.0))


def compute_stage_score(contributions: list[SignalContribution]) -> int:
    total = sum(c.contribution for c in contributions)
    return int(max(0, min(100, round(total))))


def score_to_band(stage_score: int) -> ListeningLearningStage:
    """Live metric band from stage score — does not read or write persistent stage."""
    score = max(0, min(100, int(stage_score)))
    if score >= STAGE_SCORE_BANDS[ListeningLearningStage.advanced][0]:
        return ListeningLearningStage.advanced
    if score >= STAGE_SCORE_BANDS[ListeningLearningStage.intermediate][0]:
        return ListeningLearningStage.intermediate
    return ListeningLearningStage.beginner


def band_range_label(stage: ListeningLearningStage) -> str:
    lo, hi = STAGE_SCORE_BANDS[stage]
    return f"{lo}–{hi}"


def assess_transition_eligibility(
    *,
    persistent_stage: ListeningLearningStage,
    stage_score: int,
) -> StageTransitionEligibility:
    """Eligibility for explicit transition — score entering next band is necessary, not sufficient."""
    next_min = NEXT_STAGE_MIN_SCORE.get(persistent_stage)
    if next_min is None:
        return StageTransitionEligibility(
            eligible_for_next_stage=False,
            reason="Already at Advanced — no further stage within this Official CEFR level.",
            required_conditions=("persistent_stage=advanced",),
            next_stage=None,
        )

    next_stage = ListeningLearningStage(persistent_stage + 1)
    next_name = STAGE_DISPLAY_NAMES[next_stage]
    band_label = band_range_label(next_stage)
    eligible = stage_score >= next_min

    conditions = (
        f"persistent_stage={persistent_stage.value}",
        f"stage_score>={next_min}",
        f"score_band_overlaps_{next_name.lower()}({band_label})",
        "explicit_transition_required",
    )

    if eligible:
        reason = (
            f"Stage score {stage_score} meets the {next_name} band minimum ({next_min}); "
            "explicit transition may be applied."
        )
    else:
        reason = (
            f"Stage score {stage_score} is below the {next_name} band minimum ({next_min})."
        )

    return StageTransitionEligibility(
        eligible_for_next_stage=eligible,
        reason=reason,
        required_conditions=conditions,
        next_stage=int(next_stage),
    )


def progress_toward_next_stage(
    *,
    persistent_stage: ListeningLearningStage,
    stage_score: int,
) -> float:
    """Progress (0–100) toward eligibility for the next persistent stage."""
    next_min = NEXT_STAGE_MIN_SCORE.get(persistent_stage)
    if next_min is None:
        return 100.0

    current_min = STAGE_SCORE_BANDS[persistent_stage][0]
    span = max(1, next_min - current_min)
    raw = (stage_score - current_min) / span * 100.0
    return round(max(0.0, min(100.0, raw)), 1)
