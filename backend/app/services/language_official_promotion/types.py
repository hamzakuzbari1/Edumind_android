"""Types for the Listening Official Promotion Engine (Phase 5.5)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JourneyResetSnapshot:
    learning_stage: int
    learning_stage_name: str
    promotion_readiness_score: int
    promotion_confidence: int
    transition_gate_reset: bool
    promotion_test_session_closed: bool
    preserved_exam_history: bool
    preserved_stability_history: bool
    preserved_promotion_history: bool


@dataclass(frozen=True, slots=True)
class OfficialPromotionTelemetry:
    old_cefr: str
    new_cefr: str
    promotion_test_session_id: str
    promotion_test_score: float
    promotion_test_attempt_number: int
    promotion_reason: str
    promoted_at: str
    overall_cefr_updated: bool
    previous_overall_cefr: str
    new_overall_cefr: str


@dataclass(frozen=True, slots=True)
class PromotionAppliedResult:
    old_cefr: str
    new_cefr: str
    promotion_success: bool
    new_learning_stage: int
    journey_reset: JourneyResetSnapshot
    event_id: int | None
    telemetry: OfficialPromotionTelemetry
    summary: str
    denial_reason: str | None = None


@dataclass(frozen=True, slots=True)
class PromotionTestAttemptRef:
    session_id: str
    attempt_number: int
    official_cefr: str
    target_cefr: str
    overall_score: float
    result: str
