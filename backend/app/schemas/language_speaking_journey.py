"""Pydantic schemas for Speaking S9 journey API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SpeakingJourneyStepOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = ""
    label: str = ""
    status: str = ""
    kind: str = ""


class SpeakingJourneyMissionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mission_id: str = ""
    kind: str = ""
    execution_mode: str = ""
    order_index: int = 0
    title: str = ""
    is_live: bool = False
    is_executable: bool = False


class SpeakingJourneySkillCardOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = ""
    improvement_focus: str = ""


class SpeakingJourneySupportItemOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = ""
    label: str = ""
    available: bool = False
    applied: bool = False


class SpeakingJourneyPathStepOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = ""
    purpose: str = ""
    status: str = ""
    is_task_bearing: bool = False


class SpeakingJourneyMissionSectionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = ""
    purpose: str = ""
    position: int = 0
    total: int = 0
    is_executable: bool = False
    execution_mode: str = ""
    uses_alex: bool = False


class SpeakingJourneyTaskSectionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: str = ""
    execution_mode: str = ""
    context_descriptor: str = ""
    uses_alex: bool = False
    recording_required: bool = False
    controlled_required: bool = False


class SpeakingJourneyAttemptSectionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_number: int = 0
    is_retry: bool = False
    completed_task_attempt_count: int = 0
    message: str = ""


class SpeakingJourneyNextSectionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = ""
    purpose: str = ""
    is_task_bearing: bool = False


class SpeakingJourneyTeachingBlockOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = ""
    title: str = ""
    body: str = ""


class SpeakingJourneyReadModelOut(BaseModel):
    """S12 student-safe Journey/Home projection — no internal ids or scores."""

    model_config = ConfigDict(extra="forbid")

    version: str = "12.2.1"
    official_cefr: str = ""
    internal_stage: str | None = None
    promotion_readiness: dict | None = None
    alex_daily_remaining_seconds: int | None = None
    focus_label: str = ""
    focus_reason: str = ""
    expected_outcome: str = ""
    objectives: list[str] = Field(default_factory=list)
    has_active_session: bool = False
    has_plan: bool = False
    has_blueprint: bool = False
    learning_path: list[SpeakingJourneyPathStepOut] = Field(default_factory=list)
    current_mission: SpeakingJourneyMissionSectionOut | None = None
    current_task: SpeakingJourneyTaskSectionOut | None = None
    attempt: SpeakingJourneyAttemptSectionOut | None = None
    support: list[SpeakingJourneySupportItemOut] = Field(default_factory=list)
    teaching_blocks: list[SpeakingJourneyTeachingBlockOut] = Field(default_factory=list)
    weak_skills: list[SpeakingJourneySkillCardOut] = Field(default_factory=list)
    improving_skills: list[SpeakingJourneySkillCardOut] = Field(default_factory=list)
    retention_needed: list[SpeakingJourneySkillCardOut] = Field(default_factory=list)
    transfer_needed: list[SpeakingJourneySkillCardOut] = Field(default_factory=list)
    next_mission: SpeakingJourneyNextSectionOut | None = None
    improving_skills_available: bool = False
    retention_signal_present: bool = False
    transfer_signal_present: bool = False


class SpeakingJourneyOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = "9.0.0"
    current_focus_label: str = ""
    current_focus_reason: str = ""
    session_goal: str = ""
    official_level: str = ""
    plan_summary: str = ""
    today_session_id: str = ""
    today_session_phase: str = ""
    current_activity_title: str = ""
    steps: list[SpeakingJourneyStepOut] = Field(default_factory=list)
    next_recommendation: str = ""
    has_active_session: bool = False
    practice_with_alex_available: bool = True
    today_missions: list[SpeakingJourneyMissionOut] = Field(default_factory=list)
    current_attempt_number: int = 0
    is_retry: bool = False
    completed_task_attempt_count: int = 0
    current_activity_id: str = ""
    current_activity_instructions: str = ""
    live_execution_ready: bool = False
    lesson_title: str = ""
    current_activity_kind: str = ""
    activities_total: int = 0
    activities_completed: int = 0
    activities_remaining: int = 0
    read_model: SpeakingJourneyReadModelOut | None = None


class SpeakingSessionActivityOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str = ""
    kind: str = ""
    title: str = ""
    learner_instructions: str = ""
    target_label: str = ""
    completion_criteria: list[str] = Field(default_factory=list)


class SpeakingAlexContextOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_goal: str = ""
    target_skill_label: str = ""
    communicative_scenario: str = ""
    encourage_behaviors: list[str] = Field(default_factory=list)
    elicit_behaviors: list[str] = Field(default_factory=list)
    retry_focus: str = ""
    conversation_constraints: list[str] = Field(default_factory=list)


class SpeakingSessionStartOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = ""
    live_session_id: str = ""
    blueprint_id: str = ""
    phase: str = ""
    current_activity: SpeakingSessionActivityOut | None = None
    alex_context: SpeakingAlexContextOut | None = None
    target_skill_ids: list[str] = Field(default_factory=list)
    task_prompt: str = ""


class SpeakingSessionStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    live_session_id: str = ""


class SpeakingActivityCompleteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str


class SpeakingSessionTurnIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    live_turn_id: str
    performance: float = Field(ge=0.0, le=1.0)
    success: bool = False
    source_dimension: str = ""
    mistake_tags: list[str] = Field(default_factory=list)
    mutation_applied: bool = False


class SpeakingSessionOutcomeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = ""
    outcome_kind: str = ""
    student_summary: str = ""
    retry_same_target: bool = False
    journey: SpeakingJourneyOut | None = None
