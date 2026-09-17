"""Schemas for the auto-built CEFR curriculum."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CurriculumObjectiveOut(BaseModel):
    id: str
    level: str
    title: str
    grammar: str = ""
    vocab: str = ""
    example: str = ""
    feature: str
    status: str = "new"  # new | in_progress | mastered


class CurriculumLevelOut(BaseModel):
    level: str
    status: str  # done | current | locked


class CurriculumOverviewOut(BaseModel):
    current_level: str
    next_level: str | None = None
    mastery_progress_percent: int = 0
    objectives_total: int = 0
    objectives_mastered: int = 0
    can_take_test: bool = False
    levels: list[CurriculumLevelOut] = Field(default_factory=list)
    objectives: list[CurriculumObjectiveOut] = Field(default_factory=list)


class ObjectivePracticeIn(BaseModel):
    objective_id: str


class ObjectivePracticeOut(BaseModel):
    objective_id: str
    status: str
    practice_count: int = 0


class DailyPlanItemOut(BaseModel):
    kind: str  # objective | skill | conversation | vocabulary
    title: str
    feature: str
    focus: str | None = None
    objective_id: str | None = None
    detail: str | None = None
    done: bool = False
    # Adaptive enrichment (Phase 3/2): effective level for this task + why it was chosen.
    level: str | None = None
    reason: str | None = None
    adaptive: bool = False


class DailyPlanOut(BaseModel):
    current_level: str | None = None
    mastery_progress_percent: int = 0
    objectives_mastered: int = 0
    objectives_total: int = 0
    goal: int = 0
    completed_today: int = 0
    due_vocab: int = 0
    items: list[DailyPlanItemOut] = Field(default_factory=list)
    # Renewable mission (Phase 5): current round, XP multiplier for it, and whether it can be renewed.
    round: int = 1
    xp_multiplier: float = 1.0
    renewable: bool = False
    bonus: bool = False
    coach_message: str | None = None


class DailyMissionRenewOut(BaseModel):
    renewed: bool
    round: int = 1
    xp_multiplier: float = 1.0
    reason: str | None = None


class PromotionQuestionOut(BaseModel):
    id: int
    prompt: str
    choices: list[str] = Field(default_factory=list)


class PromotionTestOut(BaseModel):
    test_id: str
    level: str
    pass_ratio: float = 0.8
    questions: list[PromotionQuestionOut] = Field(default_factory=list)


class PromotionSubmitIn(BaseModel):
    test_id: str
    answers: dict[str, int] = Field(default_factory=dict)


class PromotionResultOut(BaseModel):
    score_percent: int = 0
    correct: int = 0
    total: int = 0
    passed: bool = False
    promoted: bool = False
    new_level: str | None = None
    expired: bool = False
