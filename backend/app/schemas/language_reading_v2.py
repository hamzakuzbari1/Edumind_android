from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


CEFRLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
InternalStage = Literal["Beginner", "Intermediate", "Advanced"]
ReadingV2Mode = Literal["practice", "readiness"]
ReadingV2QuestionType = Literal["mcq", "gap_fill", "true_false", "short_answer"]


class GenerationBlueprint(BaseModel):
    cefr_level: CEFRLevel
    internal_stage: InternalStage
    mode: ReadingV2Mode = "practice"
    word_count_min: int = Field(ge=1)
    word_count_max: int = Field(ge=1)
    sentence_complexity: str
    vocabulary_difficulty: str
    target_vocab_tags: list[str] = Field(default_factory=list)
    required_vocab_items: list[str] = Field(default_factory=list)
    target_grammar_tags: list[str] = Field(default_factory=list)
    banned_above_level_grammar: list[str] = Field(default_factory=list)
    reading_subskills: list[str] = Field(default_factory=list)
    question_types: list[ReadingV2QuestionType] = Field(default_factory=list)
    student_interest: str | None = None
    topic: str
    difficulty_score: float = Field(ge=0.0, le=100.0)
    inference_depth: str
    question_count: int | None = Field(default=None, ge=1, le=20)
    number_of_questions: int = Field(ge=1, le=20)
    passage_difficulty_policy: dict[str, Any] = Field(default_factory=dict)
    safety_topic_restrictions: list[str] = Field(default_factory=list)
    prompt_version: str = "reading_v2_r8_adaptive_question_counts"
    known_vocab_items: list[str] = Field(default_factory=list)
    weak_vocab_items: list[str] = Field(default_factory=list)
    grammar_mastery_profile: dict[str, float] = Field(default_factory=dict)
    vocab_review_due_items: list[str] = Field(default_factory=list)
    recent_titles: list[str] = Field(default_factory=list)
    recent_topics: list[str] = Field(default_factory=list)
    recent_topic_tags: list[list[str]] = Field(default_factory=list)
    recent_passage_summaries: list[str] = Field(default_factory=list)
    recent_character_names: list[str] = Field(default_factory=list)
    recent_question_stems: list[str] = Field(default_factory=list)
    preferred_topic_rotation: list[str] = Field(default_factory=list)
    target_subskills: list[str] = Field(default_factory=list)
    under_sampled_subskills: list[str] = Field(default_factory=list)
    weak_subskills: list[str] = Field(default_factory=list)
    subskill_targeting_reason: str | None = None
    grammar_id: str | None = None
    grammar_title: str | None = None
    grammar_prompt_block: str | None = None

    @model_validator(mode="after")
    def _sync_question_count(self) -> "GenerationBlueprint":
        if self.question_count is None:
            self.question_count = self.number_of_questions
        return self


class GeneratedChoice(BaseModel):
    id: str
    text: str


class GeneratedQuestion(BaseModel):
    id: str
    type: str
    subskill: str
    stem: str
    sentence_with_blank: str | None = None
    display_sentence: str | None = None
    blank_prompt: str | None = None
    choices: list[GeneratedChoice] = Field(default_factory=list)
    answer_key: dict[str, Any] | None = None
    explanation: str | None = None
    evidence_quote: str | None = None


class GeneratedReadingActivity(BaseModel):
    cefr_level: CEFRLevel
    internal_stage: InternalStage
    title: str
    passage: str
    word_count: int = Field(ge=1)
    grammar_tags: list[str] = Field(default_factory=list)
    grammar_id: str | None = None
    grammar_title: str | None = None
    vocab_tags: list[str] = Field(default_factory=list)
    skill_tags: list[str] = Field(default_factory=list)
    difficulty_score: float = Field(ge=0.0, le=100.0)
    topic: str
    topic_tags: list[str] = Field(default_factory=list)
    questions: list[GeneratedQuestion] = Field(default_factory=list)
    safety_tags: list[str] = Field(default_factory=list)
    diversity_metadata: dict[str, Any] = Field(default_factory=dict)
    validation_metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    code: str
    message: str
    question_id: str | None = None


class ValidationResult(BaseModel):
    valid: bool
    validator_version: str = "reading_v2_validator_r1"
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)


class ReadingV2GenerateAttemptIn(BaseModel):
    mode: ReadingV2Mode = "practice"


class ReadingV2QuestionResultOut(BaseModel):
    question_id: str
    question_type: str
    subskill: str
    correct: bool
    score: float
    student_answer: str | None = None
    expected_answer: str | None = None
    explanation: str | None = None


class ReadingV2AttemptOut(BaseModel):
    attempt_id: int
    mode: ReadingV2Mode
    status: str
    cefr_level: CEFRLevel
    internal_stage: InternalStage
    activity: dict[str, Any]
    validation: ValidationResult
    created_at: datetime | None = None
    submitted_at: datetime | None = None
    score_percent: float | None = None


class ReadingV2SubmitAttemptIn(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    duration_seconds: int | None = Field(default=None, ge=0, le=24 * 60 * 60)


class ReadingV2SubmitAttemptOut(BaseModel):
    attempt_id: int
    score_percent: float
    passed: bool
    question_results: list[ReadingV2QuestionResultOut] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)
    next_action: str = "continue_practice"


class ReadingV2StageOut(BaseModel):
    cefr_level: CEFRLevel
    internal_stage: InternalStage
    rank: int
    status: str
    attempts_completed: int = 0
    mastery_score: float = 0.0
    recent_mastery: dict[str, Any] = Field(default_factory=dict)


class ReadingV2OverviewOut(BaseModel):
    student_id: int
    language_id: int
    current_cefr: CEFRLevel
    current_stage: InternalStage
    status: str
    readiness_target_level: CEFRLevel | None = None
    readiness_available: bool = False
    readiness_blocked_reason: str | None = None
    recent_mastery: dict[str, Any] = Field(default_factory=dict)
    next_action: str = "practice"


class ReadingV2PathOut(BaseModel):
    student_id: int
    language_id: int
    stages: list[ReadingV2StageOut] = Field(default_factory=list)


class ReadingV2HistoryItemOut(BaseModel):
    attempt_id: int
    mode: ReadingV2Mode
    status: str
    cefr_level: CEFRLevel
    internal_stage: InternalStage
    score_percent: float | None = None
    created_at: datetime | None = None
    submitted_at: datetime | None = None


class ReadingV2HistoryOut(BaseModel):
    attempts: list[ReadingV2HistoryItemOut] = Field(default_factory=list)


class ReadingV2SubmitAttemptInStrict(ReadingV2SubmitAttemptIn):
    @field_validator("answers")
    @classmethod
    def _answer_ids_must_not_be_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        return value or {}
