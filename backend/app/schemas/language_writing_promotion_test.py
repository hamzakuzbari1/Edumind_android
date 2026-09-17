"""API schemas for the Writing Promotion Assessment (WPA)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WritingPromotionEligibilityOut(BaseModel):
    eligible: bool
    reason: str
    official_cefr: str
    target_cefr: str
    readiness_score: int
    readiness_status: str


class WritingPromotionReadinessOut(BaseModel):
    official_cefr: str
    readiness_score: int
    status: str
    estimated_remaining: float
    primary_blockers: list[str] = Field(default_factory=list)


class WritingPromotionStabilityOut(BaseModel):
    promotion_confidence: int
    readiness_stability: float
    prediction: str


class WritingPromotionActiveSessionOut(BaseModel):
    session_id: str
    official_cefr: str
    target_cefr: str
    goal: str
    task_count: int


class WritingPromotionAttemptSummaryOut(BaseModel):
    session_id: str
    official_cefr: str
    target_cefr: str
    overall_score: float
    result: str


class WritingPromotionLatestResultOut(BaseModel):
    session_id: str
    overall_score: float
    result: str


class WritingPromotionStatusOut(BaseModel):
    eligibility: WritingPromotionEligibilityOut
    readiness: WritingPromotionReadinessOut
    stability: WritingPromotionStabilityOut
    active_session: WritingPromotionActiveSessionOut | None = None
    last_attempt: WritingPromotionAttemptSummaryOut | None = None
    latest_result: WritingPromotionLatestResultOut | None = None


class WritingPromotionTaskOut(BaseModel):
    task_id: str
    task_type: str
    genre: str
    prompt: str
    min_words: int
    max_words: int
    time_limit_minutes: int


class WritingPromotionStartOut(BaseModel):
    session_id: str
    official_cefr: str
    target_cefr: str
    goal: str
    tasks: list[WritingPromotionTaskOut] = Field(default_factory=list)


class WritingPromotionSubmitIn(BaseModel):
    session_id: str = Field(min_length=1)
    submissions: dict[str, str] = Field(default_factory=dict)


class WritingPromotionTaskResultOut(BaseModel):
    task_id: str
    word_count: int
    passed: bool
    score: float


class WritingPromotionSubmitOut(BaseModel):
    session_id: str
    overall_score: float
    result: str
    overall_passed: bool
    task_results: list[WritingPromotionTaskResultOut] = Field(default_factory=list)
