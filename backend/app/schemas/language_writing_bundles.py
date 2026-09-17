"""Canonical Writing bundles (W0) — closed API contracts per architecture."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WritingLifecycleState = Literal[
    "not_started",
    "mission_viewed",
    "drafting",
    "draft_submitted",
    "coach_ready",
    "revising",
    "draft_resubmitted",
    "completed",
]


class WritingFeedbackOut(BaseModel):
    """Student-facing coach output — concise, never score-only."""

    model_config = ConfigDict(extra="forbid")

    what_improved: list[str] = Field(default_factory=list)
    main_weakness: str = ""
    priority_fix: str = ""
    concrete_example: str = ""
    encouragement: str = ""
    next_focus: str = ""
    ready_to_complete: bool = False


class WritingRevisionPlanOut(BaseModel):
    """W2 canonical coach output — maps from WritingRevisionPlan."""

    model_config = ConfigDict(extra="forbid")

    encouragement: str = ""
    main_issue: str = ""
    priority_fix: str = ""
    concrete_example: str = ""
    revision_mission: str = ""
    why_it_matters: str = ""
    before_example: str = ""
    after_example: str = ""
    priority_key: str = ""
    guidance_source: str = "canonical_fallback"
    ready_to_complete: bool = False
    next_lesson_recommendation: str = ""
    what_improved: list[str] = Field(default_factory=list)


class WritingCoachMissionOut(BaseModel):
    """W2.1 coach mission layer — lesson opening after narrative builder."""

    model_config = ConfigDict(extra="forbid")

    todays_mission: str = ""
    todays_focus: str = ""
    todays_goal: str = ""
    success_criteria: list[str] = Field(default_factory=list)
    expected_learning_outcomes: list[str] = Field(default_factory=list)
    goal_label: str = ""
    mission_style: str = ""


class WritingMissionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    prompt: str
    why_today: str
    learning_goal_text: str
    task_type: str = ""
    genre: str = ""
    min_words: int = 0
    max_words: int = 0
    time_limit_minutes: int | None = None
    checklist: list[str] = Field(default_factory=list)
    scaffold_outline: list[str] = Field(default_factory=list)
    carry_forward: str = ""


class WritingComposerOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_text: str = ""
    word_count: int = 0
    can_submit: bool = True
    lifecycle: WritingLifecycleState = "drafting"


class WritingRevisionTurnOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: str
    attempt_number: int
    feedback: WritingFeedbackOut
    revision_plan: WritingRevisionPlanOut | None = None
    created_at: str


class WritingLessonExperienceMetaOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    builder_version: str = "0.1.0"
    facts_schema_version: str = "1.0.0"
    reservation_id: str | None = None


class WritingLessonExperienceBundleOut(BaseModel):
    """Canonical lesson-scoped writing bundle — no journey/progression fields."""

    model_config = ConfigDict(extra="forbid")

    lesson_id: int
    lifecycle_state: WritingLifecycleState
    official_level: str
    lesson_level: str
    lesson_title: str
    mission: WritingMissionOut
    coach_mission: WritingCoachMissionOut | None = None
    composer: WritingComposerOut = Field(default_factory=WritingComposerOut)
    coach: WritingFeedbackOut | None = None
    revision_timeline: list[WritingRevisionTurnOut] = Field(default_factory=list)
    meta: WritingLessonExperienceMetaOut = Field(default_factory=WritingLessonExperienceMetaOut)


class WritingTrendOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trend_headline: str = ""
    improvement_areas: list[str] = Field(default_factory=list)
    sustained_skills: list[str] = Field(default_factory=list)


class WritingJourneyGoalOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str


class WritingJourneyMissionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lesson_id: int | None = None
    title: str = ""
    status: str = ""
    teaser: str = ""


class WritingJourneyPromotionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = ""
    checklist: list[str] = Field(default_factory=list)
    eligible_for_level_test: bool = False
    level_test_label: str = "Writing level test"
    readiness_band: str = ""
    can_start_test: bool = False
    primary_blockers: list[str] = Field(default_factory=list)


class WritingJourneyBundleOut(BaseModel):
    """Canonical journey-scoped writing bundle — no lesson composer."""

    model_config = ConfigDict(extra="forbid")

    official_writing_level: str
    learning_stage_label: str
    personal_goal: WritingJourneyGoalOut
    todays_mission: WritingJourneyMissionOut
    weak_skills: list[str] = Field(default_factory=list)
    strong_skills: list[str] = Field(default_factory=list)
    progress_summary: str = ""
    next_milestone: str = ""
    promotion: WritingJourneyPromotionOut = Field(default_factory=WritingJourneyPromotionOut)
    trend: WritingTrendOut | None = None
    portfolio_teaser: str = ""
    meta_builder_version: str = "0.1.0"
    next_chain_id: str = ""
    next_node_id: str = ""
    lessons_completed_count: int = 0
    estimated_lessons_remaining: int = 0
    lessons_today: int = 0
    learning_stage: int = 1
    stage_score: int = 0
    readiness_score: int = 0
    readiness_band: str = ""
    can_start_wpa: bool = False
    wpa_reason: str = ""
    primary_blockers: list[str] = Field(default_factory=list)
    promotion_target: str = ""
    stability_prediction: str = ""
    active_wpa_session_id: str | None = None
    last_wpa_result: str | None = None


class WritingPromotionTaskOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_type: str
    genre: str
    prompt: str
    min_words: int
    max_words: int
    time_limit_minutes: int


class WritingPromotionBundleOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    official_level: str
    target_level: str
    goal_id: str
    goal_label: str
    tasks: list[WritingPromotionTaskOut] = Field(default_factory=list)
    status: str = "in_progress"


class WritingPortfolioEntryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: str
    mission_title: str
    mission_why: str
    first_draft_text: str
    final_draft_text: str
    coach_feedback: WritingFeedbackOut
    completion_date: str
    skills_learned: list[str] = Field(default_factory=list)
    progress_highlights: list[str] = Field(default_factory=list)


class WritingEvaluationDimensionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    status: Literal["on_track", "needs_work"]


class WritingEvaluationCriterionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    status: Literal["met", "partial", "not_met"]
    display_status: Literal[
        "met", "partially_met", "attempted_inaccurately", "not_attempted"
    ] = "not_attempted"


class WritingEvaluationDisplayOut(BaseModel):
    """Student evaluation panel — no scores."""

    model_config = ConfigDict(extra="forbid")

    dimensions: list[WritingEvaluationDimensionOut] = Field(default_factory=list)
    success_criteria: list[WritingEvaluationCriterionOut] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    ready_to_complete: bool = False
    display_version: str = "7.1.0"


class WritingLessonProgressOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    writing_stage_label: str = ""
    progress_to_next_stage: str = ""
    official_cefr: str = ""
    improved_today: list[str] = Field(default_factory=list)
    focus_next: str = ""
    what_you_did_well: list[str] = Field(default_factory=list)
    mistakes_made: list[str] = Field(default_factory=list)
    why_mistakes_happened: list[str] = Field(default_factory=list)
    improve_next: list[str] = Field(default_factory=list)
    progress_change: str = ""
    stage_proximity: str = ""
    estimated_lessons_remaining: str = ""
    journey_update: str = ""
    history_comparison: list[str] = Field(default_factory=list)
    progress_version: str = "7.2.0"
    feedback_version: str = "7.2.0"


class WritingGrammarNoteOut(BaseModel):
    """One grammar issue explained like a teacher — why, rule, fix, example."""

    model_config = ConfigDict(extra="forbid")

    issue: str
    rule: str = ""
    fix: str = ""
    example: str = ""


class WritingEducationalAnalysisOut(BaseModel):
    """Teacher-style educational read of the draft — enrichment only, never pass/fail."""

    model_config = ConfigDict(extra="forbid")

    available: bool = False
    source: str = ""
    provider: str = ""
    model_name: str = ""
    analyzer_version: str = ""
    task_response: str = ""
    topic_understanding: str = ""
    coherence: str = ""
    organization: str = ""
    idea_development: str = ""
    goal_alignment: str = ""
    vocabulary: str = ""
    vocabulary_range: str = ""
    vocabulary_suggestions: list[str] = Field(default_factory=list)
    repeated_words: list[str] = Field(default_factory=list)
    missing_topic_words: list[str] = Field(default_factory=list)
    grammar_notes: list[WritingGrammarNoteOut] = Field(default_factory=list)
    cefr_estimate: str = ""
    cefr_reason: str = ""
    progress_comparison: str = ""
    learning_diagnosis: str = ""
    revision_priority: str = ""
    encouragement: str = ""
    strengths: list[str] = Field(default_factory=list)
    analysis_version: str = "2.0.0"


class WritingDraftSubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_text: str
    complete_if_ready: bool = False


class WritingDraftSubmitOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_item_id: int
    draft_id: str
    word_count: int
    revision_number: int
    completed: bool
    ready_to_complete: bool
    lifecycle: str
    feedback: WritingFeedbackOut
    revision_plan: WritingRevisionPlanOut
    evaluation_display: WritingEvaluationDisplayOut
    educational_analysis: WritingEducationalAnalysisOut = Field(default_factory=WritingEducationalAnalysisOut)
    lesson_progress: WritingLessonProgressOut | None = None
    completion: dict[str, object] = Field(default_factory=dict)
    comparison: dict[str, object] | None = None
    runtime_version: str


class WritingGenerateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str | None = None
    chain_id: str | None = None
    node_id: str | None = None
    official_cefr: str | None = None


class WritingGenerateOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_item_id: int
    title: str
    prompt: str
    mission_title: str
    writing_context: str
    instructions: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    learning_outcomes: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    expected_output: str
    min_words: int
    max_words: int
    blueprint_hash: str
    generation_hash: str
    outcome: str | None = None
    provider_name: str | None = None
    model_name: str | None = None
    goal: str
    official_cefr: str
    chain_id: str | None = None
    node_id: str | None = None
    selection_reason: str | None = None
    runtime_version: str
