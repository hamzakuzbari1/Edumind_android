"""Schemas for self-contained Grammar & Vocabulary teaching lessons."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LessonPracticeOut(BaseModel):
    question: str
    answer: str


class LessonOut(BaseModel):
    id: str
    level: str
    type: str  # grammar | vocabulary
    title: str
    explanation: str
    examples: list[str] = Field(default_factory=list)
    practice: list[LessonPracticeOut] = Field(default_factory=list)


class LessonListOut(BaseModel):
    level: str
    lessons: list[LessonOut] = Field(default_factory=list)
