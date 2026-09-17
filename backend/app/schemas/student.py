from pydantic import BaseModel, Field


class LessonAssetOut(BaseModel):
    asset_type: str
    url: str | None = None


class LessonCardOut(BaseModel):
    id: int
    title: str
    subject: str
    grade: str
    teacherName: str
    preview: str
    pdfUrl: str | None = None
    icon: str = "mdi-book-open-page-variant"


class LessonDetailOut(BaseModel):
    id: int
    courseId: int | None = None
    title: str
    subject: str
    grade: str
    teacherName: str
    teacherImageUrl: str | None = None
    preview: str
    pdfUrl: str | None = None
    videoUrl: str | None = None
    assets: list[LessonAssetOut] = []
    has_video: bool = False
    has_pdf: bool = False
    has_ai_chat: bool = False
    has_generated_quiz: bool = False
    ai_status: str = "draft"
    ai_ready: bool = False
    quiz_ready: bool = False
    ai_processing: bool = False
    ai_error: bool = False
    error_message: str | None = None
    chunk_count: int = 0
    quiz_question_count: int = 0
    lessonSummary: list[str] = []
    keywords: list[str] = []
    chatMessages: list[dict] = []
    quizQuestions: list[dict] = []
    voiceTtsAvailable: bool = True
    voiceTtsMessage: str | None = None


class ChatRequest(BaseModel):
    lesson_id: int
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    messages: list[dict]
    question: str | None = None
    audio_url: str | None = None
    sources: list[dict] = []
    voiceTtsAvailable: bool = True
    voiceTtsMessage: str | None = None


class QuizQuestionOut(BaseModel):
    id: int
    question: str
    options: list[str]
    hint: str | None = None


class QuizSubmitRequest(BaseModel):
    lesson_id: int
    answers: dict[str, int]  # question_id -> selected_index


class RemedialQuizRequest(BaseModel):
    answers: dict[str, int]  # question_id -> selected_index


class QuizSubmitResponse(BaseModel):
    correct_count: int
    total: int
    feedback: list[dict]
    score_percent: int


class ProfileUpdate(BaseModel):
    # Academic subject interests (stored in interests_json)
    interests: list[str] = []
    # Personal hobbies for examples/analogies (stored in hobbies_json)
    hobbies: list[str] = []
    difficulty: str = "medium"
    age: int | None = Field(default=None, ge=5, le=25)
    learning_style: str = "theoretical"
    future_goal: str = "undecided"
    preferred_explanation_style: str = "normal"
    personality_mode: str = "friendly_teacher"


class ProfileOut(BaseModel):
    interests: list[str]
    hobbies: list[str]
    difficulty: str
    age: int | None = None
    learning_style: str
    future_goal: str
    preferred_explanation_style: str
    personality_mode: str
