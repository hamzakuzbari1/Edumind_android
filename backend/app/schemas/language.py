from datetime import date, datetime

from pydantic import BaseModel, Field


class LanguageSkillLevelsOut(BaseModel):
    reading: str | None = None
    listening: str | None = None
    writing: str | None = None
    speaking: str | None = None
    primary_focus_skill: str | None = None
    primary_focus_label_ar: str | None = None
    strength_skill: str | None = None
    strength_label_ar: str | None = None


class PlacementCorrectionOut(BaseModel):
    original: str = ""
    corrected: str = ""
    rule: str = ""


class PlacementRecommendationOut(BaseModel):
    """The placement exam's actionable guidance, surfaced on the hub to steer first lessons."""

    topic: str = ""
    weakest_skill: str = ""
    summary: str = ""
    corrections: list[PlacementCorrectionOut] = Field(default_factory=list)


class LanguageProductOut(BaseModel):
    id: int
    slug: str
    name_ar: str
    description_ar: str | None = None
    price: float
    currency: str
    term_days: int


class LanguageAccessOut(BaseModel):
    subscribed: bool
    status: str = "pending"
    expires_at: datetime | None = None
    activated_at: datetime | None = None
    placement_completed: bool = False
    next_allowed_retake_date: datetime | None = None
    onboarding_step: str | None = None
    product: LanguageProductOut | None = None
    levels: LanguageSkillLevelsOut = Field(default_factory=LanguageSkillLevelsOut)
    target_level: str | None = None
    target_date: date | None = None
    target_progress_percent: int | None = None
    estimated_time_to_next_level: str | None = None
    certificate_level: str | None = None
    certificate_awarded_at: datetime | None = None
    placement_recommendation: PlacementRecommendationOut | None = None
    redirect: str | None = None


class LanguageSubscribeRequest(BaseModel):
    method: str = "card"


class LanguagePlacementSkipRequest(BaseModel):
    baseline_level: str = Field(default="B1", pattern="^(A1|A2|B1|B2|C1|C2)$")


class LanguageSubscribeOut(BaseModel):
    ok: bool = True
    reference: str
    unlocked: bool = True
    status: str = "active"
