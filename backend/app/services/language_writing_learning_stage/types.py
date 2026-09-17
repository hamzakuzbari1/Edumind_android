"""Writing learning stage types — Stage 1–3 within official CEFR band."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class WritingLearningStage(IntEnum):
    beginner = 1
    intermediate = 2
    advanced = 3


_STAGE_LABELS = {
    WritingLearningStage.beginner: "Building foundations",
    WritingLearningStage.intermediate: "Developing fluency",
    WritingLearningStage.advanced: "Approaching promotion",
}


def writing_stage_label(*, official_cefr: str, stage: WritingLearningStage | int) -> str:
    s = WritingLearningStage(max(1, min(3, int(stage))))
    return f"{official_cefr.upper()} · {_STAGE_LABELS[s]}"


@dataclass(frozen=True, slots=True)
class WritingSignalSnapshot:
    """Signals gathered from writing progression state — not lesson count alone.

    All signals are derived from persisted `WritingEvaluationEngineResult` facts
    (per-lesson continuous scores), never from lesson count. Lesson count is
    exposure only and is a supporting gate requirement, never a stage driver.
    """

    official_cefr: str
    grammar_mastery_avg: float
    vocabulary_mastery_avg: float
    revision_quality_avg: float
    confidence_avg: float
    confidence_trend: float
    evidence_coverage_avg: float
    recent_stability: float
    lesson_index: int
    completed_nodes: int
    pending_weak_skills: int
    # Extended educational signals (from WritingEvaluationEngineResult)
    task_response_avg: float = 0.5
    organization_avg: float = 0.5
    cefr_alignment_avg: float = 0.6
    repeated_mistake_ratio: float = 0.0


@dataclass(frozen=True, slots=True)
class WritingStageTransitionEligibility:
    eligible_for_next_stage: bool
    reason: str
    required_conditions: tuple[str, ...]
    next_stage: int | None


@dataclass(frozen=True, slots=True)
class WritingLearningStageResult:
    official_cefr: str
    current_stage: WritingLearningStage
    stage_score: int
    stage_band: str
    eligible_for_next_stage: bool
    next_stage: int | None
    progress_to_next: float
    primary_blocker: str | None
    grammar_mastery_avg: float
    vocabulary_mastery_avg: float
    revision_quality_avg: float
    confidence_avg: float
    evidence_coverage_avg: float
    stability_avg: float
    lesson_index: int
    task_response_avg: float = 0.5
    organization_avg: float = 0.5
    cefr_alignment_avg: float = 0.6
