"""Learning stage telemetry (Phase 5.1 / 5.1.1)."""

from __future__ import annotations

from app.services.language_learning_stage.types import (
    LearningStageResult,
    LearningStageTelemetry,
    ListeningLearningStage,
    SignalContribution,
    StageTransitionEligibility,
    stage_label,
)


def build_stage_result(
    *,
    official_cefr: str,
    persistent_stage: ListeningLearningStage,
    stage_score: int,
    stage_band: ListeningLearningStage,
    eligibility: StageTransitionEligibility,
    contributions: list[SignalContribution],
    progress_to_next: float,
    lesson_index: int,
    mastered_objectives: int,
    total_objectives: int,
    transition_gate=None,
) -> LearningStageResult:
    next_name = (
        stage_label(official_cefr=official_cefr, stage=eligibility.next_stage)
        if eligibility.next_stage is not None
        else None
    )
    telemetry = LearningStageTelemetry(
        official_cefr=official_cefr,
        persistent_stage=int(persistent_stage),
        stage_score=stage_score,
        stage_band=int(stage_band),
        signal_contributions=tuple(contributions),
        lesson_index=lesson_index,
        mastered_objectives=mastered_objectives,
        total_objectives=total_objectives,
        eligibility=eligibility,
        transition_gate=transition_gate,
    )
    return LearningStageResult(
        official_cefr=official_cefr,
        current_stage=int(persistent_stage),
        stage_name=stage_label(official_cefr=official_cefr, stage=persistent_stage),
        stage_score=stage_score,
        stage_band=int(stage_band),
        stage_band_name=stage_label(official_cefr=official_cefr, stage=stage_band),
        eligible_for_next_stage=eligibility.eligible_for_next_stage,
        eligibility_reason=eligibility.reason,
        next_stage=eligibility.next_stage,
        next_stage_name=next_name,
        transition_requirements=eligibility.required_conditions,
        progress_to_next=progress_to_next,
        telemetry=telemetry,
    )
