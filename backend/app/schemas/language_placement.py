from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PlacementSpeakingUploadOut(BaseModel):
    ok: bool = True
    media_object_id: int
    public_url: str | None = None


class PlacementHistorySkillOut(BaseModel):
    """One skill score owned by the same immutable legacy assessment."""

    skill: str
    score_percent: float
    level: str


class PlacementHistoryResultOut(BaseModel):
    """A self-contained placement snapshot; never mixed with live analytics."""

    record_id: str
    assessment_id: int | None = None
    exam_session_id: str | None = None
    attempt_id: int | None = None
    language_id: int
    source: Literal["legacy", "ai_exam"]
    overall_level: str
    overall_calculation_method: str
    completed_at: datetime
    skills: list[PlacementHistorySkillOut] = Field(default_factory=list)


class PlacementHistoryListOut(BaseModel):
    available: bool
    results: list[PlacementHistoryResultOut] = Field(default_factory=list)


class PlacementHistoryLatestOut(BaseModel):
    available: bool
    result: PlacementHistoryResultOut | None = None
