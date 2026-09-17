"""Pydantic schemas for guided conversation scenarios."""

from pydantic import BaseModel, Field


class ScenarioScoresOut(BaseModel):
    communication: int = 0
    grammar: int = 0
    vocabulary: int = 0
    fluency: int = 0


class ScenarioRecommendedOut(BaseModel):
    id: int
    title_en: str
    title_ar: str
    category: str
    level_min: str


class ScenarioOut(BaseModel):
    id: int
    scenario_key: str
    category: str
    category_label_en: str = ""
    category_label_ar: str = ""
    title_en: str
    title_ar: str
    description_en: str | None = None
    description_ar: str | None = None
    level_min: str
    target_skills: list[str] = Field(default_factory=list)
    ai_role: str
    student_role: str
    opening_message: str = ""
    locked: bool = False
    recommended: bool = False


class ScenarioListOut(BaseModel):
    scenarios: list[ScenarioOut] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)


class ScenarioDetailOut(ScenarioOut):
    effective_level: str
    student_level: str


class ScenarioStartOut(BaseModel):
    session_id: int
    scenario: ScenarioOut
    opening_message: str
    opening_line: str
    ai_role: str
    student_role: str
    effective_level: str


class ScenarioMessageOut(BaseModel):
    role: str
    text: str = ""
    content: str = ""
    reply_audio_url: str | None = None


class ScenarioSessionOut(BaseModel):
    session_id: int
    status: str
    scenario: ScenarioOut
    messages: list[ScenarioMessageOut] = Field(default_factory=list)
    turn_count: int = 0
    effective_level: str = "A1"
    summary: dict | None = None


class ScenarioTurnIn(BaseModel):
    session_id: int
    text: str


class ScenarioTurnOut(BaseModel):
    turn_index: int
    assistant_reply: str
    session_id: int
    effective_level: str = "A1"
    user_transcript: str | None = None
    reply_audio_url: str | None = None


class ScenarioEndIn(BaseModel):
    session_id: int


class ScenarioEndOut(BaseModel):
    scores: ScenarioScoresOut
    what_went_well: list[str] = Field(default_factory=list)
    what_to_improve: list[str] = Field(default_factory=list)
    recommended_next_scenario: ScenarioRecommendedOut | None = None
    overall_impression: str = ""
    strengths: list[str] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
    vocabulary_suggestions: list[str] = Field(default_factory=list)
    estimated_cefr: str = "A1"
    encouragement: str = ""
    scenario: ScenarioOut | None = None
