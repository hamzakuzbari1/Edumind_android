"""API schemas for Speaking Promotion Assessment (SPA) — S18 student-safe surfaces."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SpeakingPromotionAssessmentStatusOut(BaseModel):
    available: bool
    spa_unlocked: bool
    source_cefr: str | None = None
    target_cefr: str | None = None
    estimated_duration_seconds: int = 0
    status: str = "unavailable"
    assessment_id: str | None = None
    task_count: int = 0
    has_interaction_coverage_gaps: bool = False
    message: str = ""


class SpeakingPromotionAssessmentTaskOut(BaseModel):
    task_id: str
    task_order: int
    task_family: str
    execution_mode: str
    scenario: str
    student_prompt: str
    follow_up_prompts: list[str] = Field(default_factory=list)
    context_descriptor: str = ""
    max_duration_seconds: int = 0
    preparation_seconds: int = 0
    spontaneous_production_required: bool = False
    spontaneous_interaction_required: bool = False


class SpeakingPromotionAssessmentCreateOut(BaseModel):
    assessment_id: str
    blueprint_id: str
    status: str
    source_cefr: str
    target_cefr: str
    task_count: int
    frozen: bool
    has_interaction_coverage_gaps: bool = False
    tasks: list[SpeakingPromotionAssessmentTaskOut] = Field(default_factory=list)


class SpeakingPromotionAssessmentGetOut(BaseModel):
    assessment_id: str
    blueprint_id: str
    status: str
    source_cefr: str
    target_cefr: str
    task_count: int
    frozen: bool
    has_interaction_coverage_gaps: bool = False
    tasks: list[SpeakingPromotionAssessmentTaskOut] = Field(default_factory=list)
    created_at: str = ""
