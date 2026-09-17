"""Transition gate thresholds and requirement evaluators (Phase 5.2).

All thresholds live here — the engine reads them; nothing is hardcoded elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_learning_stage.types import ListeningLearningStage
from app.services.language_transition_gate.types import GateRequirementResult, TransitionGateContext

REQUIREMENT_STAGE_SCORE = "stage_score"
REQUIREMENT_CONFIDENCE = "confidence"
REQUIREMENT_EVIDENCE = "evidence_coverage"
REQUIREMENT_OBJECTIVE_MASTERY = "objective_mastery"
REQUIREMENT_CHALLENGE_STABILITY = "challenge_stability"
REQUIREMENT_REVIEW_COMPLETION = "review_completion"
REQUIREMENT_RECENT_CONSISTENCY = "recent_consistency"
REQUIREMENT_LESSON_EXPOSURE = "minimum_lesson_exposure"

ALL_REQUIREMENTS: tuple[str, ...] = (
    REQUIREMENT_STAGE_SCORE,
    REQUIREMENT_CONFIDENCE,
    REQUIREMENT_EVIDENCE,
    REQUIREMENT_OBJECTIVE_MASTERY,
    REQUIREMENT_CHALLENGE_STABILITY,
    REQUIREMENT_REVIEW_COMPLETION,
    REQUIREMENT_RECENT_CONSISTENCY,
    REQUIREMENT_LESSON_EXPOSURE,
)


@dataclass(frozen=True, slots=True)
class TransitionGateThresholds:
    min_stage_score: int
    min_confidence: float
    min_evidence_coverage: float
    min_objective_mastery: float
    min_challenge_score: float
    max_demote_streak: int
    min_review_completion: float
    max_pending_reviews: int
    min_recent_consistency: float
    min_lesson_exposure: int


# Keyed by (from_stage, to_stage).
GATE_THRESHOLDS: dict[tuple[int, int], TransitionGateThresholds] = {
    (
        int(ListeningLearningStage.beginner),
        int(ListeningLearningStage.intermediate),
    ): TransitionGateThresholds(
        min_stage_score=40,
        min_confidence=0.75,
        min_evidence_coverage=0.65,
        min_objective_mastery=0.45,
        min_challenge_score=0.50,
        max_demote_streak=0,
        min_review_completion=0.70,
        max_pending_reviews=0,
        min_recent_consistency=0.55,
        min_lesson_exposure=6,
    ),
    (
        int(ListeningLearningStage.intermediate),
        int(ListeningLearningStage.advanced),
    ): TransitionGateThresholds(
        min_stage_score=80,
        min_confidence=0.80,
        min_evidence_coverage=0.72,
        min_objective_mastery=0.60,
        min_challenge_score=0.58,
        max_demote_streak=0,
        min_review_completion=0.78,
        max_pending_reviews=0,
        min_recent_consistency=0.62,
        min_lesson_exposure=12,
    ),
}


def _pct(value: float) -> str:
    return f"{round(value * 100):d}"


def thresholds_for_stage(persistent_stage: int) -> tuple[int, TransitionGateThresholds] | None:
    stage = max(1, min(3, int(persistent_stage)))
    if stage >= int(ListeningLearningStage.advanced):
        return None
    next_stage = stage + 1
    key = (stage, next_stage)
    thresholds = GATE_THRESHOLDS.get(key)
    if thresholds is None:
        return None
    return next_stage, thresholds


def evaluate_stage_score(ctx: TransitionGateContext, t: TransitionGateThresholds) -> GateRequirementResult:
    passed = ctx.stage_score >= t.min_stage_score
    return GateRequirementResult(
        name=REQUIREMENT_STAGE_SCORE,
        current=str(ctx.stage_score),
        required=str(t.min_stage_score),
        passed=passed,
        message=(
            f"Stage score {ctx.stage_score} meets the minimum ({t.min_stage_score})."
            if passed
            else f"Stage score {ctx.stage_score} is below the minimum ({t.min_stage_score})."
        ),
    )


def evaluate_confidence(ctx: TransitionGateContext, t: TransitionGateThresholds) -> GateRequirementResult:
    passed = ctx.confidence_avg >= t.min_confidence
    return GateRequirementResult(
        name=REQUIREMENT_CONFIDENCE,
        current=f"{ctx.confidence_avg:.2f}",
        required=f"{t.min_confidence:.2f}",
        passed=passed,
        message=(
            f"Listening confidence {_pct(ctx.confidence_avg)}% meets the minimum ({_pct(t.min_confidence)}%)."
            if passed
            else f"Listening confidence {_pct(ctx.confidence_avg)}% is below the minimum ({_pct(t.min_confidence)}%)."
        ),
    )


def evaluate_evidence(ctx: TransitionGateContext, t: TransitionGateThresholds) -> GateRequirementResult:
    passed = ctx.evidence_coverage_avg >= t.min_evidence_coverage
    return GateRequirementResult(
        name=REQUIREMENT_EVIDENCE,
        current=_pct(ctx.evidence_coverage_avg),
        required=_pct(t.min_evidence_coverage),
        passed=passed,
        message=(
            f"Evidence coverage {_pct(ctx.evidence_coverage_avg)}% meets the minimum ({_pct(t.min_evidence_coverage)}%)."
            if passed
            else f"Evidence coverage too low ({_pct(ctx.evidence_coverage_avg)}% / {_pct(t.min_evidence_coverage)}%)."
        ),
    )


def evaluate_objective_mastery(ctx: TransitionGateContext, t: TransitionGateThresholds) -> GateRequirementResult:
    passed = ctx.objective_mastery_ratio >= t.min_objective_mastery
    return GateRequirementResult(
        name=REQUIREMENT_OBJECTIVE_MASTERY,
        current=_pct(ctx.objective_mastery_ratio),
        required=_pct(t.min_objective_mastery),
        passed=passed,
        message=(
            f"Objective mastery {_pct(ctx.objective_mastery_ratio)}% meets the minimum ({_pct(t.min_objective_mastery)}%)."
            if passed
            else (
                f"Objective mastery {_pct(ctx.objective_mastery_ratio)}% is below "
                f"the minimum ({_pct(t.min_objective_mastery)}%)."
            )
        ),
    )


def evaluate_challenge_stability(ctx: TransitionGateContext, t: TransitionGateThresholds) -> GateRequirementResult:
    level_ok = ctx.challenge_level.lower() in {"normal", "hard", "exam"}
    score_ok = ctx.challenge_score >= t.min_challenge_score
    streak_ok = ctx.demote_streak <= t.max_demote_streak
    passed = level_ok and score_ok and streak_ok
    label = ctx.challenge_level.replace("_", " ").title() or "Unknown"
    return GateRequirementResult(
        name=REQUIREMENT_CHALLENGE_STABILITY,
        current=label,
        required="Normal",
        passed=passed,
        message=(
            f"Challenge level {label} is stable."
            if passed
            else f"Challenge stability insufficient (level={label}, demote_streak={ctx.demote_streak})."
        ),
    )


def evaluate_review_completion(ctx: TransitionGateContext, t: TransitionGateThresholds) -> GateRequirementResult:
    no_pending = ctx.pending_review_count <= t.max_pending_reviews
    ratio_ok = ctx.review_completion_ratio >= t.min_review_completion
    passed = no_pending and ratio_ok
    if ctx.pending_review_count > 0:
        current = "Pending"
        message = f"{ctx.pending_review_count} review lesson(s) still pending."
    elif not ratio_ok:
        current = _pct(ctx.review_completion_ratio)
        message = (
            f"Review completion {_pct(ctx.review_completion_ratio)}% is below "
            f"the minimum ({_pct(t.min_review_completion)}%)."
        )
    else:
        current = _pct(ctx.review_completion_ratio)
        message = "Review lessons are complete."
    return GateRequirementResult(
        name=REQUIREMENT_REVIEW_COMPLETION,
        current=current,
        required=_pct(t.min_review_completion),
        passed=passed,
        message=message,
    )


def evaluate_recent_consistency(ctx: TransitionGateContext, t: TransitionGateThresholds) -> GateRequirementResult:
    passed = ctx.recent_consistency >= t.min_recent_consistency
    return GateRequirementResult(
        name=REQUIREMENT_RECENT_CONSISTENCY,
        current=_pct(ctx.recent_consistency),
        required=_pct(t.min_recent_consistency),
        passed=passed,
        message=(
            f"Recent listening consistency {_pct(ctx.recent_consistency)}% meets the minimum."
            if passed
            else f"Recent listening consistency {_pct(ctx.recent_consistency)}% is below "
            f"the minimum ({_pct(t.min_recent_consistency)}%)."
        ),
    )


def evaluate_lesson_exposure(ctx: TransitionGateContext, t: TransitionGateThresholds) -> GateRequirementResult:
    passed = ctx.lesson_index >= t.min_lesson_exposure
    return GateRequirementResult(
        name=REQUIREMENT_LESSON_EXPOSURE,
        current=str(ctx.lesson_index),
        required=str(t.min_lesson_exposure),
        passed=passed,
        message=(
            f"Lesson exposure {ctx.lesson_index} meets the minimum ({t.min_lesson_exposure})."
            if passed
            else f"Insufficient lesson exposure ({ctx.lesson_index} / {t.min_lesson_exposure})."
        ),
    )


def evaluate_all_requirements(
    ctx: TransitionGateContext,
    thresholds: TransitionGateThresholds,
) -> tuple[GateRequirementResult, ...]:
    return (
        evaluate_stage_score(ctx, thresholds),
        evaluate_confidence(ctx, thresholds),
        evaluate_evidence(ctx, thresholds),
        evaluate_objective_mastery(ctx, thresholds),
        evaluate_challenge_stability(ctx, thresholds),
        evaluate_review_completion(ctx, thresholds),
        evaluate_recent_consistency(ctx, thresholds),
        evaluate_lesson_exposure(ctx, thresholds),
    )


def requirement_progress(req: GateRequirementResult) -> float:
    """Normalized progress toward passing one requirement (0–100)."""
    if req.passed:
        return 100.0
    try:
        current_num = float(req.current.rstrip("%"))
        required_num = float(req.required.rstrip("%"))
        if required_num > 0:
            return max(0.0, min(99.0, current_num / required_num * 100.0))
    except ValueError:
        pass
    return 0.0
