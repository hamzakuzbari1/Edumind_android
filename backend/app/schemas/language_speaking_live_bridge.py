"""Pydantic schemas for M10 Live Speaking Bridge API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LiveBridgePrepareIn(BaseModel):
    package_id: str | None = None


class LiveBridgeRehearsalStartIn(BaseModel):
    package_id: str | None = None


class LiveBridgeRehearsalTurnIn(BaseModel):
    student_text: str = Field(..., min_length=1, max_length=4000)


class LiveBridgeOut(BaseModel):
    journey_phase: str = ""
    package_id: str = ""
    preparation: dict[str, Any] | None = None
    rehearsal: dict[str, Any] | None = None
    voice_session: dict[str, Any] | None = None
    live_context: dict[str, Any] | None = None
    discussion_summary: str = ""
    ready_for_live: bool = False


class LiveBridgeRespondNextLine(BaseModel):
    speaker: str = ""
    text: str = ""


class LiveBridgeRespondOut(BaseModel):
    """M12 voice turn response — the server owns the entire conversation.

    Everything the client renders (transcript, correction, next line) comes from
    here; the client only records audio and plays the returned audio.
    """

    heard: bool = True
    student_transcript: str = ""
    stt_confidence: float | None = None
    provider: str = ""
    decision: str | None = None
    micro_correction: str | None = None
    coaching_note: str | None = None
    next_line: LiveBridgeRespondNextLine = Field(default_factory=LiveBridgeRespondNextLine)
    audio_b64: str | None = None
    audio_mime: str | None = None
    bridge: LiveBridgeOut | None = None
