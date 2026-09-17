"""Schemas for Speaking Lesson Runtime E2."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LessonRuntimeOpenIn(BaseModel):
    package_id: str | None = None
    force_restart: bool = False


class LessonRuntimeMarkVocabIn(BaseModel):
    vocabulary_id: str


class LessonRuntimeMarkBlockIn(BaseModel):
    block_id: str


class LessonRuntimeOut(BaseModel):
    runtime_version: str
    state: dict[str, Any]
    package: dict[str, Any]
    constraints_summary: dict[str, Any] = Field(default_factory=dict)
    section_progress: dict[str, Any] = Field(default_factory=dict)
