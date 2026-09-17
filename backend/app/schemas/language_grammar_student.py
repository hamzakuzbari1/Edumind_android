"""Pydantic schemas for Student Grammar Module (Product Milestone A + Wave D)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GrammarModuleStatusOut(BaseModel):
    enabled: bool


class GrammarTopicOut(BaseModel):
    grammar_id: str
    display_name: str
    cefr_band: str = ""


class GrammarDashboardOut(BaseModel):
    enabled: bool
    current_cefr: str = ""
    current_grammar_topic: GrammarTopicOut | None = None
    grammar_target: str | None = None
    difficulty: str = "guided"
    estimated_minutes: int = 10
    lesson_goal: str = ""
    has_lesson_preview: bool = False
    empty_state_message: str = ""


class GrammarMistakeOut(BaseModel):
    incorrect: str
    correct: str


class GrammarLessonOut(BaseModel):
    lesson_id: str
    lesson_schema_version: str = ""
    methodology_version: str = ""
    revision_id: str = ""
    canonical_revision_id: str = ""
    grammar_id: str = ""
    display_name: str = ""
    cefr_level: str = ""
    grammar_target: str
    lesson_title: str
    student_content: dict[str, Any] = Field(default_factory=dict)
    teacher_opening: str
    lesson_goal: str
    warmup: str
    main_activity: str
    follow_up_questions: list[str] = Field(default_factory=list)
    common_mistakes: list[GrammarMistakeOut] = Field(default_factory=list)
    expected_patterns: list[str] = Field(default_factory=list)
    completion_message: str = ""
    estimated_minutes: int = 10
    difficulty: str = "guided"
    pipeline_id: str = ""
    activity_id: str = ""
    generation_mode: str = "generate_only"
    authoring_status: str = "ready"
    retry_message: str = ""
    # Wave D — server-issued session for attested completion
    activity_session_id: str = ""


class GrammarLessonStartIn(BaseModel):
    language_id: int = 1
    use_llm_authoring: bool = True
    grammar_id: str | None = None


class GrammarPracticePreviewEvaluateIn(BaseModel):
    revision_id: str = Field(min_length=8)
    item_id: str = Field(min_length=1)
    learner_response: Any
    attempt_number: int = Field(default=1, ge=1, le=2)


class GrammarPracticePreviewEvaluateOut(BaseModel):
    correct: bool
    feedback: str
    hint: str | None = None
    may_continue: bool
    attempt_number: int


class GrammarLessonChatCreateIn(BaseModel):
    revision_id: str = Field(min_length=8)


class GrammarLessonChatMessageOut(BaseModel):
    id: str
    role: str
    content: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class GrammarLessonChatSessionOut(BaseModel):
    session_id: str
    revision_id: str
    status: str
    mode: str = "preview"
    welcome_message: str = ""
    messages: list[GrammarLessonChatMessageOut] = Field(default_factory=list)


class GrammarLessonChatSendIn(BaseModel):
    revision_id: str | None = Field(default=None, min_length=8)
    message: str = Field(min_length=1, max_length=800)
    section_key: str | None = Field(default=None, max_length=64)
    block_context: dict[str, Any] | None = None


class GrammarLessonChatSendOut(BaseModel):
    session_id: str
    revision_id: str
    user_message: GrammarLessonChatMessageOut
    assistant_message: GrammarLessonChatMessageOut
    messages: list[GrammarLessonChatMessageOut] = Field(default_factory=list)


class GrammarLessonChatAudioIn(BaseModel):
    revision_id: str | None = Field(default=None, min_length=8)


class GrammarLessonChatAudioOut(BaseModel):
    audio_url: str
    mime_type: str = "audio/wav"
    voice_provider: str = "supertonic"


class GrammarActivityCompleteIn(BaseModel):
    """Wave D — server-attested completion. Client must not send grammar_id/score."""

    activity_session_id: str = Field(min_length=8)
    language_id: int = 1
    # Evaluation payload only — never grammar_id / mastery / unlock / score
    answers: dict[str, Any] | list[Any] | None = None
    response_text: str = ""


class GrammarActivityCompleteOut(BaseModel):
    grammar_id: str
    mastery_state: str
    overall_mastery: float = 0.0
    evidence_was_new: bool = True
    synced_completed_ids: list[str] = Field(default_factory=list)
    current_grammar_id: str | None = None
    next_grammar_id: str | None = None
    unlocked_ids: list[str] = Field(default_factory=list)
    observation_id: str = ""
    activity_session_id: str = ""
