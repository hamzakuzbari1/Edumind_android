from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class QuizQuestionBase(BaseModel):
    question_type: str
    question_text: str
    options: list[str] | None = None
    correct_answer: dict | str | bool | int | None = None
    points: int = 1
    sort_order: int = 0


class QuizQuestionCreate(QuizQuestionBase):
    pass


class QuizQuestionUpdate(BaseModel):
    question_type: str | None = None
    question_text: str | None = None
    options: list[str] | None = None
    correct_answer: dict | str | bool | int | None = None
    points: int | None = None
    sort_order: int | None = None


class QuizQuestionOut(BaseModel):
    id: int
    question_type: str
    question_text: str
    options: list[str] = Field(default_factory=list)
    points: int
    sort_order: int
    requires_manual_grading: bool
    correct_answer: dict | str | bool | int | None = None


class QuizQuestionStudentOut(BaseModel):
    id: int
    question_type: str
    question_text: str
    options: list[str] = Field(default_factory=list)
    points: int
    sort_order: int
    requires_manual_grading: bool


class CourseQuizCreate(BaseModel):
    title: str
    description: str | None = None
    duration_minutes: int | None = None
    passing_score_percent: int = 60
    is_published: bool = False
    due_at: datetime | None = None

    @field_validator("passing_score_percent", mode="before")
    @classmethod
    def _coerce_passing_score(cls, value):
        if value is None or value == "":
            return 60
        return value

    @field_validator("duration_minutes", mode="before")
    @classmethod
    def _coerce_duration(cls, value):
        if value is None or value == "":
            return None
        return value


class CourseQuizUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    duration_minutes: int | None = None
    passing_score_percent: int | None = None
    is_published: bool | None = None
    due_at: datetime | None = None

    @field_validator("duration_minutes", mode="before")
    @classmethod
    def _coerce_duration(cls, value):
        if value is None or value == "":
            return None
        return value


class CourseQuizOut(BaseModel):
    id: int
    course_id: int
    title: str
    description: str | None = None
    duration_minutes: int | None = None
    passing_score_percent: int
    is_published: bool
    due_at: str | None = None
    question_count: int = 0
    total_points: int = 0
    attempt_count: int = 0
    created_at: str | None = None


class CourseQuizDetailOut(CourseQuizOut):
    questions: list[QuizQuestionOut] = Field(default_factory=list)


class SaveAnswerItem(BaseModel):
    question_id: int
    answer: dict | str | bool | int | None = None


class SaveAnswersRequest(BaseModel):
    answers: list[SaveAnswerItem]


class GradeEssayRequest(BaseModel):
    points_earned: float
    teacher_feedback: str | None = None
    publish: bool = True


class QuizAnswerOut(BaseModel):
    question_id: int
    question_type: str
    question_text: str
    answer: dict | str | bool | int | None = None
    points_earned: float | None = None
    max_points: int
    is_correct: bool | None = None
    teacher_feedback: str | None = None
    requires_manual_grading: bool = False
    pending_grading: bool = False


class QuizAttemptOut(BaseModel):
    id: int
    quiz_id: int
    student_id: int
    student_name: str | None = None
    status: str
    score: float
    max_score: float
    percent: float | None = None
    passed: bool | None = None
    started_at: str | None = None
    submitted_at: str | None = None
    graded_at: str | None = None
    answers: list[QuizAnswerOut] = Field(default_factory=list)


class QuizAttemptSummaryOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    status: str
    score: float
    max_score: float
    percent: float | None = None
    passed: bool | None = None
    submitted_at: str | None = None
    pending_essay_count: int = 0


class QuizResultsOut(BaseModel):
    quiz: CourseQuizOut
    attempts: list[QuizAttemptSummaryOut] = Field(default_factory=list)


class StudentQuizListItem(BaseModel):
    id: int
    course_id: int
    title: str
    description: str | None = None
    duration_minutes: int | None = None
    passing_score_percent: int
    due_at: str | None = None
    question_count: int
    total_points: int = 0
    attempt_status: str | None = None
    percent: float | None = None
    passed: bool | None = None
    score: float | None = None
    max_score: float | None = None


class StudentQuizTakeOut(BaseModel):
    quiz: StudentQuizListItem
    questions: list[QuizQuestionStudentOut]
    attempt_id: int | None = None
    answers: dict[int, dict | str | bool | int | None] = Field(default_factory=dict)
    time_remaining_seconds: int | None = None


class QuizAnalyticsOut(BaseModel):
    quiz_id: int
    quiz_title: str
    enrolled_students: int
    attempted_count: int
    completion_rate: float
    average_score: float | None = None
    highest_score: float | None = None
    lowest_score: float | None = None
    ranking: list[dict] = Field(default_factory=list)


class CourseQuizAnalyticsOut(BaseModel):
    course_id: int
    course_title: str
    quiz_count: int
    enrolled_students: int
    total_attempts: int
    average_score: float | None = None
    completion_rate: float
    quizzes: list[QuizAnalyticsOut] = Field(default_factory=list)
