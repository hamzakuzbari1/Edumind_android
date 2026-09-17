"""Schemas for Guided Discussion E3 (Live Voice Discussion)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DiscussionOpenIn(BaseModel):
    package_id: str | None = None
    force_restart: bool = False


class DiscussionSubmitIn(BaseModel):
    student_response: str = Field(min_length=1, max_length=4000)


class DiscussionRuntimeOut(BaseModel):
    runtime_version: str
    state: dict[str, Any]
    package_title: str = ""
    current_step: dict[str, Any] | None = None
    steps_total: int = 0
    opening_move: str = ""
    closing_move: str = ""
    latest_assistant: dict[str, Any] | None = None
    provider: str = ""
    package_snippet: dict[str, Any] = Field(default_factory=dict)
    # Ephemeral voice fields (GPT TTS) — never load-bearing
    audio_b64: str | None = None
    audio_mime: str | None = None
    student_transcript: str | None = None
    heard: bool | None = None
