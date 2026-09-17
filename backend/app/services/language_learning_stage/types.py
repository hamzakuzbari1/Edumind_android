"""Types for the Listening Learning Stage Engine (Phase 5.1 / 5.1.1).

Learning stages are internal bands *within* an Official CEFR level (e.g. A2 Beginner).
They are NOT CEFR levels and must never mutate Official CEFR.

Phase 5.1.1: current_stage is persistent; stage_score is a live metric only.
Score bands do NOT auto-change the stored stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class ListeningLearningStage(IntEnum):
    """Three internal stages within one Official CEFR band (listening only)."""

    beginner = 1
    intermediate = 2
    advanced = 3


STAGE_DISPLAY_NAMES: dict[ListeningLearningStage, str] = {
    ListeningLearningStage.beginner: "Beginner",
    ListeningLearningStage.intermediate: "Intermediate",
    ListeningLearningStage.advanced: "Advanced",
}


def stage_label(*, official_cefr: str, stage: ListeningLearningStage | int) -> str:
    """Human-readable stage name, e.g. 'A2 Intermediate'."""
    st = ListeningLearningStage(stage) if not isinstance(stage, ListeningLearningStage) else stage
    return f"{official_cefr.upper()} {STAGE_DISPLAY_NAMES[st]}"


@dataclass(frozen=True, slots=True)
class SignalContribution:
    """One weighted listening signal contribution to the stage score."""

    signal: str
    raw_value: float
    normalized: float  # 0..1
    weight: float
    contribution: float  # normalized * weight * 100


@dataclass
class ListeningSignalSnapshot:
    """Raw listening-only inputs gathered from existing Phase 1–3 engines."""

    official_cefr: str
    confidence_avg: float = 0.0
    confidence_mastery_avg: float = 0.0
    evidence_coverage_avg: float = 0.0
    challenge_score: float = 0.5
    curriculum_progression: float = 0.0
    objective_mastery_ratio: float = 0.0
    review_completion_ratio: float = 0.0
    recent_stability: float = 0.5
    lesson_index: int = 0
    mastered_objectives: int = 0
    total_objectives: int = 0
    challenge_level: str = "normal"
    demote_streak: int = 0
    pending_review_count: int = 0
    review_due_objectives: tuple[str, ...] = ()
    needs_evidence_objectives: tuple[str, ...] = ()
    missing_speaker_evidence: bool = False
    missing_inference_evidence: bool = False


@dataclass(frozen=True, slots=True)
class StageTransitionEligibility:
    """Whether the learner may transition to the next persistent stage (explicit action only)."""

    eligible_for_next_stage: bool
    reason: str
    required_conditions: tuple[str, ...]
    next_stage: int | None


@dataclass(frozen=True, slots=True)
class LearningStageTelemetry:
    official_cefr: str
    persistent_stage: int
    stage_score: int
    stage_band: int
    signal_contributions: tuple[SignalContribution, ...]
    lesson_index: int = 0
    mastered_objectives: int = 0
    total_objectives: int = 0
    eligibility: StageTransitionEligibility | None = None
    transition_gate: object | None = None


@dataclass(frozen=True, slots=True)
class LearningStageResult:
    """Output of the Learning Stage Engine."""

    official_cefr: str
    current_stage: int
    stage_name: str
    stage_score: int
    stage_band: int
    stage_band_name: str
    eligible_for_next_stage: bool
    eligibility_reason: str
    next_stage: int | None
    next_stage_name: str | None
    transition_requirements: tuple[str, ...]
    progress_to_next: float
    telemetry: LearningStageTelemetry
