"""API schemas for the Listening Promotion Test (PR-2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PromotionTestEligibilityOut(BaseModel):
    eligible: bool
    reason: str
    official_cefr: str
    target_cefr: str
    readiness_score: int
    readiness_status: str


class PromotionTestReadinessOut(BaseModel):
    official_cefr: str
    readiness_score: int
    status: str
    estimated_remaining: float
    primary_blockers: list[str] = Field(default_factory=list)


class PromotionTestStabilityOut(BaseModel):
    promotion_confidence: int
    readiness_stability: float
    prediction: str


class PromotionTestActiveSessionOut(BaseModel):
    session_id: str
    official_cefr: str
    target_cefr: str
    attempt_number: int
    assessment_count: int
    expires_at: datetime


class PromotionTestAttemptSummaryOut(BaseModel):
    session_id: str
    attempt_number: int
    official_cefr: str
    target_cefr: str
    overall_score: float
    result: str


class PromotionTestLatestResultOut(BaseModel):
    session_id: str
    overall_score: float
    result: str
    recommendation: str
    objective_scores: dict[str, float] = Field(default_factory=dict)


class PromotionTestStatusOut(BaseModel):
    eligibility: PromotionTestEligibilityOut
    readiness: PromotionTestReadinessOut
    stability: PromotionTestStabilityOut
    active_session: PromotionTestActiveSessionOut | None = None
    last_attempt: PromotionTestAttemptSummaryOut | None = None
    latest_result: PromotionTestLatestResultOut | None = None


class PromotionTestAssessmentOut(BaseModel):
    assessment_id: str
    lesson_id: str
    objective_id: str
    objective_label: str
    situation: str
    format: str
    speaker_count: int
    difficulty_band: str
    question: str
    choices: list[str]
    sequence_index: int


class PromotionTestStartOut(BaseModel):
    session_id: str
    official_cefr: str
    target_cefr: str
    attempt_number: int
    expires_at: datetime
    assessments: list[PromotionTestAssessmentOut]


class PromotionTestSubmitIn(BaseModel):
    session_id: str = Field(min_length=1)
    answers: dict[str, int] = Field(default_factory=dict)


class PromotionTestScoreBreakdownOut(BaseModel):
    overall_score: float
    objective_scores: dict[str, float] = Field(default_factory=dict)
    evidence_score: float
    consistency_score: float
    coverage_score: float
    exam_confidence: float


class PromotionTestSubmitOut(BaseModel):
    session_id: str
    overall_score: float
    result: str
    objective_scores: dict[str, float] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendation: str
    score_breakdown: PromotionTestScoreBreakdownOut
    attempt_number: int
    official_cefr: str
    target_cefr: str
    assessments_correct: int
    assessments_total: int
