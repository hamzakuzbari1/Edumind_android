"""API schemas for Listening Official Promotion (PR-3)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JourneyResetOut(BaseModel):
    learning_stage: int
    learning_stage_name: str
    promotion_readiness_score: int
    promotion_confidence: int
    transition_gate_reset: bool
    promotion_test_session_closed: bool
    preserved_exam_history: bool
    preserved_stability_history: bool
    preserved_promotion_history: bool


class OfficialPromotionTelemetryOut(BaseModel):
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


class ListeningOfficialPromotionOut(BaseModel):
    promotion_success: bool
    old_cefr: str
    new_cefr: str
    new_learning_stage: int
    journey_reset: JourneyResetOut
    summary: str
    recommended_next_lesson: str | None = None
    telemetry: OfficialPromotionTelemetryOut
    event_id: int | None = None
    reason: str | None = None
