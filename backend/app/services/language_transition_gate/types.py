"""Types for the Listening Transition Gate (Phase 5.2).

All requirements use AND logic — no single metric unlocks promotion.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class GateRequirementResult:
    name: str
    current: str
    required: str
    passed: bool
    message: str


@dataclass(frozen=True, slots=True)
class TransitionGateContext:
    """Listening-only inputs gathered from Phase 1–3 engines and learning stage."""

    official_cefr: str
    persistent_stage: int
    stage_score: int
    confidence_avg: float
    evidence_coverage_avg: float
    objective_mastery_ratio: float
    challenge_score: float
    challenge_level: str
    demote_streak: int
    review_completion_ratio: float
    pending_review_count: int
    recent_consistency: float
    lesson_index: int
    mastered_objectives: int = 0
    total_objectives: int = 0
    needs_evidence_objectives: tuple[str, ...] = ()
    review_due_objectives: tuple[str, ...] = ()
    missing_speaker_evidence: bool = False
    missing_inference_evidence: bool = False


@dataclass(frozen=True, slots=True)
class TransitionGateResult:
    eligible: bool
    overall_gate_score: float
    requirements: tuple[GateRequirementResult, ...]
    passed_requirements: tuple[str, ...]
    failed_requirements: tuple[str, ...]
    recommendations: tuple[str, ...]
    estimated_remaining_progress: float
    primary_blocker: str | None = None
    next_stage: int | None = None
    official_cefr: str = ""
    persistent_stage: int = 1
