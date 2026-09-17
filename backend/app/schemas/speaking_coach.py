"""Request/response models for the AI speaking coach."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CoachTurnIn(BaseModel):
    session_id: str = Field(..., description="Stable per-conversation id (the frontend owns it).")
    transcript: str = Field(..., description="Learner speech-to-text (may contain glued words).")
    cefr_level: str = Field("A1", description="A1 | A2 | B1 | B2 | C1 | C2")
    defer_explanation: bool = Field(
        True, description="True = fast turn + explanation in background (low latency)."
    )


class CoachTurnOut(BaseModel):
    turn_id: str
    user_sentence_evaluated: str
    corrected_sentence: str
    explanation: str
    ai_reply: str
    explanation_pending: bool = False


class CoachExplanationOut(BaseModel):
    turn_id: str
    explanation: str | None = None
    ready: bool = False
