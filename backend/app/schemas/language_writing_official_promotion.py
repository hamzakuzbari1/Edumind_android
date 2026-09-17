"""API schemas for Writing Official Promotion."""

from __future__ import annotations

from pydantic import BaseModel


class WritingOfficialPromotionOut(BaseModel):
    promotion_success: bool
    old_cefr: str
    new_cefr: str
    new_learning_stage: int
    summary: str
    session_id: str = ""
    reason: str | None = None
