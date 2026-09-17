from datetime import date, datetime

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DictionaryEntryOut(BaseModel):
    part_of_speech: str = ""
    definition: str = ""
    examples: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)


class DictionarySearchOut(BaseModel):
    """Global dictionary search: exact-word entries + prefix suggestions."""

    query: str = ""
    entries: list[DictionaryEntryOut] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    total_words: int = 0


class WordAnalysisIn(BaseModel):
    word: str = Field(min_length=1, max_length=64)
    level: str = "A2"

    @field_validator("word")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = " ".join((v or "").split())
        if not v:
            raise ValueError("word cannot be empty")
        return v


class WordAnalysisOut(BaseModel):
    """On-demand vocabulary metadata — English only (the platform is English-only)."""

    word: str
    part_of_speech: str = ""
    definition: str = ""
    example_sentence: str = ""
    pronunciation_tip: str = ""
    synonyms: list[str] = Field(default_factory=list)
    cefr_level: str = ""


class VocabularyChallengeOut(BaseModel):
    """Daily fill-in-the-blanks review challenge — English only (the platform is English-only)."""

    words: list[str] = Field(default_factory=list)        # the target words being reviewed
    paragraph_challenge: str = ""                          # text with [blank1], [blank2], ... placeholders
    context_hint: str = ""                                 # short English hint about the paragraph's meaning
    blanks_mapping: dict[str, str] = Field(default_factory=dict)  # {"[blank1]": "word", ...}
    options_pool: list[str] = Field(default_factory=list)  # correct words + distractors (shuffled)


class VocabularyChallengeResultItem(BaseModel):
    word: str = Field(min_length=1, max_length=64)
    correct: bool


class VocabularyChallengeSubmitIn(BaseModel):
    """Per-blank results of a finished daily challenge, fed to the learner model (English only)."""

    results: list[VocabularyChallengeResultItem] = Field(default_factory=list)


class VocabularyChallengeSubmitOut(BaseModel):
    recorded: int = 0
    correct: int = 0
    total: int = 0


class LearnerComponentOut(BaseModel):
    """One knowledge component's mastery for the current learner (English only)."""

    code: str
    skill: str
    category: str
    cefr_level: str
    p_mastery: float = 0.0
    confidence: float = 0.0
    evidence_count: int = 0
    next_review_at: datetime | None = None


class LearnerModelProfileOut(BaseModel):
    """Unified learner-model snapshot: per-component mastery + per-skill confidence + due count."""

    components: list[LearnerComponentOut] = Field(default_factory=list)
    skill_confidence: dict[str, float] = Field(default_factory=dict)
    due_count: int = 0


class LearnerPracticeItemOut(BaseModel):
    """One adaptive practice MCQ targeting a weak component (English only)."""

    component_code: str
    skill: str
    cefr_level: str
    stem: str
    choices: list[str] = Field(default_factory=list)
    correct_index: int = 0


class LearnerPracticeSetOut(BaseModel):
    items: list[LearnerPracticeItemOut] = Field(default_factory=list)


class LearnerPracticeResultItem(BaseModel):
    component_code: str = Field(min_length=1, max_length=64)
    correct: bool


class LearnerPracticeSubmitIn(BaseModel):
    results: list[LearnerPracticeResultItem] = Field(default_factory=list)


class LearnerPracticeSubmitOut(BaseModel):
    recorded: int = 0
    correct: int = 0
    total: int = 0


class LessonProgressOut(BaseModel):
    status: str = "not_started"
    score_percent: float | None = None
    completed_at: datetime | None = None
    attempt_count: int = 0


class LessonListItemOut(BaseModel):
    id: int
    title: str
    level: str
    sort_order: int
    progress: LessonProgressOut
    audio_available: bool | None = None


class LessonListOut(BaseModel):
    student_level: str
    lesson_level: str | None = None
    lessons: list[LessonListItemOut] = Field(default_factory=list)


class LessonQuestionOut(BaseModel):
    id: str
    type: str = "mcq"
    stem: str
    choices: list[str]


class GlossaryItemOut(BaseModel):
    word: str
    definition: str = ""


class ReadingLessonOut(BaseModel):
    id: int
    title: str
    level: str
    passage: str
    passage_ar: str | None = None
    glossary: list[GlossaryItemOut] = Field(default_factory=list)
    questions: list[LessonQuestionOut]
    progress: LessonProgressOut


class ListeningLessonOut(BaseModel):
    id: int
    title: str
    level: str
    instructions: str | None = None
    questions: list[LessonQuestionOut]
    audio_url: str | None = None
    audio_available: bool = False
    progress: LessonProgressOut


class LessonSubmitIn(BaseModel):
    answers: dict[str, dict] = Field(default_factory=dict)
    duration_seconds: int | None = None  # reading: time spent on the passage, for WPM


class ReadingQuestionResultOut(BaseModel):
    id: str | None = None
    type: str = "detail"
    stem: str = ""
    selected_index: int | None = None
    correct_index: int | None = None
    is_correct: bool = False
    explanation: str = ""
    evidence_quote: str = ""


class LessonSubmitOut(BaseModel):
    content_item_id: int
    score_percent: float
    passed: bool
    status: str
    attempt_count: int
    completed_at: datetime | None = None
    correct_count: int
    total_questions: int
    # Reading: per-question correctness + teaching explanation + supporting quote (others omit it).
    question_results: list[ReadingQuestionResultOut] = Field(default_factory=list)
    reading_wpm: int | None = None  # reading speed (words/min) when a duration was reported
    transcript: str | None = None  # listening: the script, revealed after submitting


class VocabularySaveIn(BaseModel):
    word: str = Field(min_length=1, max_length=64)


class VocabularySaveOut(BaseModel):
    saved: bool = False
    word: str = ""


class ReadingAudioOut(BaseModel):
    public_url: str | None = None
    available: bool = False


class ReadingTopicsOut(BaseModel):
    options: list[str] = Field(default_factory=list)
    selected: list[str] = Field(default_factory=list)


class ReadingTopicsIn(BaseModel):
    topics: list[str] = Field(default_factory=list)


class ReadingHistoryItemOut(BaseModel):
    id: int
    title: str
    level: str | None = None
    topic: str | None = None
    score_percent: float | None = None
    completed_at: datetime | None = None


class SkillMasteryItemOut(BaseModel):
    code: str
    mastery: int = 0


class ReadingInsightsOut(BaseModel):
    wpm_recent: list[int] = Field(default_factory=list)
    avg_wpm: int | None = None
    best_wpm: int | None = None
    avg_comprehension: float | None = None
    lessons_completed: int = 0
    weak_skills: list[SkillMasteryItemOut] = Field(default_factory=list)
    strong_skills: list[SkillMasteryItemOut] = Field(default_factory=list)


class ReadingExplainIn(BaseModel):
    sentence: str = Field(min_length=1, max_length=600)
    level: str = "A2"


class ReadingExplainOut(BaseModel):
    explanation: str = ""


class ReadingSummaryIn(BaseModel):
    summary: str = Field(min_length=1, max_length=2000)


class ReadingSummaryOut(BaseModel):
    score_percent: float = 0.0
    feedback: str = ""
    covered_points: list[str] = Field(default_factory=list)
    missed_points: list[str] = Field(default_factory=list)


class SkillGrowthSkillOut(BaseModel):
    level: str | None = None
    growth_percent: int = 0
    lessons_completed: int = 0
    lessons_total: int = 0
    average_score_percent: float | None = None


class SkillGrowthOut(BaseModel):
    reading: SkillGrowthSkillOut | None = None
    listening: SkillGrowthSkillOut | None = None
    writing: SkillGrowthSkillOut | None = None
    speaking: SkillGrowthSkillOut | None = None
    vocabulary: dict | None = None


class VocabularyMetricsOut(BaseModel):
    total_words: int = 0
    known_words: int = 0
    learning_words: int = 0
    new_words: int = 0
    reviewed_today: int = 0
    daily_review_goal: int = 10


class VocabularyCardOut(BaseModel):
    id: int
    word: str
    translation_ar: str | None = None
    example: str | None = None
    example_ar: str | None = None
    part_of_speech: str | None = None
    level: str | None = None
    status: str = "new"
    enriched: bool = True
    review_count: int = 0
    last_reviewed_at: datetime | None = None
    next_review_at: datetime | None = None
    due: bool = True
    is_difficult: bool = False
    image_url: str | None = None


class VocabularyListOut(BaseModel):
    student_level: str
    lesson_level: str | None = None
    metrics: VocabularyMetricsOut
    cards: list[VocabularyCardOut] = Field(default_factory=list)


class VocabularyReviewIn(BaseModel):
    # SM-2 recall grade 0-5 (1=Again, 3=Hard, 4=Good, 5=Easy).
    quality: int = Field(ge=0, le=5)


class VocabularyAiWordOut(BaseModel):
    """One AI-generated vocabulary word — English only (the platform is English-only)."""

    content_id: int | None = None
    word: str
    part_of_speech: str = ""
    definition: str = ""
    example_sentence: str = ""
    example_sentence_ar: str = ""
    translation_ar: str = ""
    image_prompt: str = ""
    cefr_level: str = ""


class VocabularyAiGenerateOut(BaseModel):
    words: list[VocabularyAiWordOut] = Field(default_factory=list)
    generated_today: int = 0
    remaining_today: int = 10  # mirrors language_vocabulary_service.AI_GENERATION_DAILY_LIMIT


class VocabQuizItemOut(BaseModel):
    """One quiz item — the target word is deliberately NOT included until after the
    student submits a spelling guess (see VocabQuizSpellingOut.correct_word)."""

    item_id: int  # = the word's LanguageContentItem id
    definition: str = ""
    example_masked: str = ""


class VocabQuizOut(BaseModel):
    items: list[VocabQuizItemOut] = Field(default_factory=list)
    total: int = 0
    already_completed_today: bool = False


class VocabQuizSpellingIn(BaseModel):
    item_id: int
    guess: str = Field(default="", max_length=80)


class VocabQuizSpellingOut(BaseModel):
    correct: bool
    near_miss: bool
    correct_word: str


class VocabQuizResultItemIn(BaseModel):
    item_id: int
    spelling_correct: bool = False
    spelling_near_miss: bool = False
    pronunciation_score: int | None = Field(default=None, ge=0, le=100)


class VocabQuizCompleteIn(BaseModel):
    results: list[VocabQuizResultItemIn] = Field(default_factory=list)


class VocabQuizCompleteOut(BaseModel):
    spelling_correct: int = 0
    spelling_total: int = 0
    pronunciation_average: float = 0.0
    recorded: bool = True


class WritingPromptOut(BaseModel):
    id: int
    title: str
    level: str | None = None
    prompt: str
    prompt_ar: str | None = None
    min_words: int = 20
    min_sentences: int = 2
    target_component: str | None = None
    target_focus: str | None = None
    practice_hint: str | None = None
    task_type: str | None = None
    topic: str | None = None
    exercise_type: str | None = None
    word_bank: list[str] = Field(default_factory=list)
    sentence_starters: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    mini_lesson: dict | None = None
    rewrite_instruction: str | None = None
    recommended: bool = False
    recommendation_reason: str = ""
    progress: dict = Field(default_factory=dict)


class WritingListOut(BaseModel):
    student_level: str
    lesson_level: str | None = None
    recommended_prompt_id: int | None = None
    recommended_reason: str = ""
    writing_profile: dict = Field(default_factory=dict)
    prompts: list[WritingPromptOut] = Field(default_factory=list)


class WritingSubmitIn(BaseModel):
    response_text: str


class WritingSubmitOut(BaseModel):
    prompt_id: int
    score_percent: float
    passed: bool
    word_count: int
    sentence_count: int
    completed_at: datetime | None = None
    status: str
    criteria: dict = Field(default_factory=dict)
    flags: dict = Field(default_factory=dict)
    feedback: str = ""
    next_focus: dict = Field(default_factory=dict)
    target_component: str | None = None
    target_focus: str | None = None
    scoring_version: str = ""
    meets_threshold: bool = False
    attempt_number: int = 1
    previous_score_percent: float | None = None
    improvement_percent: float | None = None
    rewrite_required: bool = False
    rewrite_prompt: str = ""
    mini_lesson: dict | None = None


class SpeakingPromptOut(BaseModel):
    id: int
    title: str
    level: str | None = None
    prompt: str
    prompt_ar: str | None = None
    min_seconds: int = 20
    progress: dict = Field(default_factory=dict)


class SpeakingListOut(BaseModel):
    student_level: str
    lesson_level: str | None = None
    prompts: list[SpeakingPromptOut] = Field(default_factory=list)


class SpeakingSubmitIn(BaseModel):
    media_object_id: int
    duration_seconds: int | None = None


class SpeakingSubmitOut(BaseModel):
    prompt_id: int
    media_object_id: int
    public_url: str | None = None
    duration_seconds: int | None = None
    score_percent: float
    passed: bool
    completed_at: datetime | None = None
    status: str
    transcript: str | None = None
    correction_text: str | None = None
    grammar_errors: list[dict] = Field(default_factory=list)
    reply: str | None = None
    reply_audio_url: str | None = None


class ShadowSentenceOut(BaseModel):
    id: int
    text: str
    level: str
    source: str = "level"


class ShadowSentenceListOut(BaseModel):
    level: str
    sentences: list[ShadowSentenceOut] = Field(default_factory=list)
    focus: str | None = None


class ShadowSubmitOut(BaseModel):
    transcript: str | None = None
    similarity: int
    overall_score: int
    words: list[dict] = Field(default_factory=list)
    weak_words: list[str] = Field(default_factory=list)
    note: str | None = None
    passed: bool


class LanguageHubPlacementOut(BaseModel):
    completed_at: datetime | None = None
    overall_level: str | None = None
    can_retake: bool = False
    next_allowed_retake_date: datetime | None = None


class LanguageHubPathOut(BaseModel):
    path_id: int | None = None
    generated_at: datetime | None = None
    items_total: int = 0
    items_completed: int = 0


class LanguageHubOut(BaseModel):
    levels: dict[str, str | None] = Field(default_factory=dict)
    skill_growth: SkillGrowthOut = Field(default_factory=SkillGrowthOut)
    target_level: str | None = None
    target_date: date | None = None
    placement: LanguageHubPlacementOut | None = None
    learning_path: LanguageHubPathOut = Field(default_factory=LanguageHubPathOut)
    quick_stats: dict[str, int | float] = Field(default_factory=dict)


class ActivityEventItemOut(BaseModel):
    id: int
    event_type: str
    skill: str | None = None
    title: str | None = None
    score_percent: float | None = None
    created_at: datetime


class SpeakingCorrectionDisplayOut(BaseModel):
    has_errors: bool = False
    no_correction_message: str | None = None
    your_sentence: str | None = None
    corrected_sentence: str | None = None
    explanation: str | None = None
    speech_prefix: str | None = None


class SpeakingConversationMessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    turn_index: int | None = None
    evaluation: dict | None = None
    correction_display: SpeakingCorrectionDisplayOut | None = None
    reply_audio_url: str | None = None
    reply_audio_pending: bool = False


class SpeakingTurnCorrectionOut(BaseModel):
    has_errors: bool = False
    original: str = ""
    corrected: str = ""
    errors: list[dict] = Field(default_factory=list)


class SpeakingTurnScoresOut(BaseModel):
    fluency: int = 0
    grammar: int = 0
    vocabulary: int = 0
    confidence: int = 0


class SpeakingTurnEvaluationOut(BaseModel):
    correction: SpeakingTurnCorrectionOut = Field(default_factory=SpeakingTurnCorrectionOut)
    correction_display: SpeakingCorrectionDisplayOut | None = None
    scores: SpeakingTurnScoresOut = Field(default_factory=SpeakingTurnScoresOut)
    estimated_cefr: str | None = None
    coaching_note_ar: str | None = None
    grammar_tool_used: bool = False
    topic: str | None = None
    reply_audio_pending: bool = False


class SpeakingConversationStateOut(BaseModel):
    session_id: int | None = None
    effective_speaking_level: str | None = None
    turn_count: int = 0
    messages: list[SpeakingConversationMessageOut] = Field(default_factory=list)
    welcome_hint: str | None = None


class SpeakingConversationTurnOut(BaseModel):
    session_id: int
    turn_index: int
    transcript: str
    evaluation: SpeakingTurnEvaluationOut
    correction_display: SpeakingCorrectionDisplayOut
    reply: str
    reply_audio_url: str | None = None
    reply_audio_pending: bool = False
    effective_speaking_level: str | None = None
    level_changed: bool = False
    timing_ms: dict[str, int] = Field(default_factory=dict)


class SpeakingConversationProgressOut(BaseModel):
    effective_speaking_level: str | None = None
    placement_baseline_level: str | None = None
    conversation_turns_total: int = 0
    sessions_completed: int = 0
    average_scores: SpeakingTurnScoresOut = Field(default_factory=SpeakingTurnScoresOut)
    level_trend: str | None = None
    last_conversation_at: datetime | None = None
    next_level: str | None = None
    mastery_progress_percent: int = 0
    rolling_mastery_score: int = 0
    turns_in_window: int = 0
    mastery_window: int = 8
    mastered: bool = False


class SpeakingConversationResetOut(BaseModel):
    ok: bool = True


class LanguageProgressOut(BaseModel):
    overall_level: str | None = None
    reading_level: str | None = None
    listening_level: str | None = None
    writing_level: str | None = None
    speaking_level: str | None = None
    skill_growth: SkillGrowthOut = Field(default_factory=SkillGrowthOut)
    completed_activities: int = 0
    reading_completion_percent: int = 0
    listening_completion_percent: int = 0
    vocabulary_count: int = 0
    vocabulary_learned: int = 0
    vocabulary_learning: int = 0
    writing_completed: int = 0
    speaking_completed: int = 0
    writing_completion_percent: int = 0
    speaking_completion_percent: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    recent_activity: list[ActivityEventItemOut] = Field(default_factory=list)
    target_level: str | None = None
    target_date: date | None = None
