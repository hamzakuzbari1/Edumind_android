"""API schemas for Speaking Official Promotion (S20)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SpeakingOfficialPromotionIn(BaseModel):
    assessment_id: str | None = None
    attempt_id: str | None = None


class SpeakingOfficialPromotionOut(BaseModel):
    promotion_success: bool
    old_cefr: str
    new_cefr: str
    new_learning_stage: int = 0
    summary: str = ""
    reason: str | None = None
    assessment_id: str = ""
    attempt_id: str = ""
    promoted_at: str = ""
    already_promoted: bool = False
    ready_for_new_journey: bool = False
