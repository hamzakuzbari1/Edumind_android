"""Pydantic schemas for adaptive progression (Phase 7.5)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AdaptiveSkillStateOut(BaseModel):
    current_level: str
    rolling_average: float | None = None
    recommendation: str
    recent_scores: list[float] = Field(default_factory=list)
    window_size: int = 8
    samples_in_window: int = 0
    consecutive_pass: int = 0
    consecutive_fail: int = 0
    up_threshold: float = 82.0
    down_threshold: float = 40.0


class AdaptiveStateOut(BaseModel):
    current_level: str
    rolling_average: float | None = None
    recommendation: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    objectives_in_progress: int = 0
    objectives_mastered: int = 0
    objectives_total: int = 0
    skills: dict[str, AdaptiveSkillStateOut] = Field(default_factory=dict)
