"""Learning Journey API schemas (Phase G)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JourneyStageOut(BaseModel):
    grammar_id: str
    display_code: str = ""
    display_name: str
    stage_index: int
    status: str
    mastery_state: str = "unknown"
    overall_mastery: float = 0.0
    estimated_minutes: int = 18
    skills: list[str] = Field(default_factory=list)


class JourneyLevelOut(BaseModel):
    cefr: str
    status: str
    expanded: bool = False
    completed_count: int = 0
    total_count: int = 0
    stages: list[JourneyStageOut] = Field(default_factory=list)


class JourneyProgressOut(BaseModel):
    cefr_label: str = ""
    stage_index: int = 0
    stage_total_in_level: int = 0
    level_percent: float = 0.0
    overall_completed: int = 0
    overall_total: int = 0


class LearningJourneyOut(BaseModel):
    enabled: bool = False
    anchor_cefr: str = ""
    current_grammar_id: str | None = None
    next_grammar_id: str | None = None
    curriculum_version: str = ""
    progress: JourneyProgressOut = Field(default_factory=JourneyProgressOut)
    levels: list[JourneyLevelOut] = Field(default_factory=list)
    schema_version: int = 1
