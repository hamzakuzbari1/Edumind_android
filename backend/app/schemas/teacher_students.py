from pydantic import BaseModel, Field

from app.schemas.gamification import GamificationProfileOut


class TeacherStudentDirectoryRowOut(BaseModel):
    student_id: int
    full_name: str
    email: str
    grade: int | None = None
    is_active: bool = True
    last_activity_at: str | None = None
    completion_percent: int = 0
    avg_quiz_percent: int = 0
    enrolled_subjects: list[str] = Field(default_factory=list)


class TeacherStudentSearchOut(BaseModel):
    students: list[TeacherStudentDirectoryRowOut] = Field(default_factory=list)
    total: int = 0


class TeacherStudentInfoOut(BaseModel):
    student_id: int
    full_name: str
    email: str
    grade: int | None = None
    registration_date: str | None = None
    last_login_at: str | None = None
    account_status: str = "active"


class TeacherStudentCourseOut(BaseModel):
    course_id: int
    title: str
    subject_name: str
    grade: int
    subscription_status: str = "active"
    progress_percent: int = 0
    completed_lessons: int = 0
    total_lessons: int = 0


class TeacherStudentSubscriptionOut(BaseModel):
    product_name: str
    language_code: str | None = None
    payment_status: str
    activated_at: str | None = None
    expires_at: str | None = None


class TeacherStudentLearningOut(BaseModel):
    enrolled_subjects: list[str] = Field(default_factory=list)
    subscriptions: list[TeacherStudentSubscriptionOut] = Field(default_factory=list)
    active_courses: int = 0
    completed_courses: int = 0
    lessons_completed: int = 0
    lessons_remaining: int = 0
    courses: list[TeacherStudentCourseOut] = Field(default_factory=list)


class TeacherStudentQuizAttemptOut(BaseModel):
    id: int
    quiz_title: str
    course_title: str
    subject_name: str
    score_percent: int = 0
    passed: bool | None = None
    submitted_at: str | None = None
    source: str = "manual"


class TeacherStudentQuizAnalyticsOut(BaseModel):
    total_completed: int = 0
    average_score_percent: int = 0
    best_score_percent: int = 0
    lowest_score_percent: int = 0
    recent_attempts: list[TeacherStudentQuizAttemptOut] = Field(default_factory=list)


class TeacherStudentLanguageOut(BaseModel):
    language_code: str = "en"
    language_name: str = "English"
    reading_level: str | None = None
    listening_level: str | None = None
    writing_level: str | None = None
    speaking_level: str | None = None
    overall_cefr_level: str | None = None
    vocabulary_progress_percent: int = 0
    vocabulary_count: int = 0
    writing_progress_percent: int = 0
    speaking_progress_percent: int = 0
    certificates_earned: list[str] = Field(default_factory=list)
    current_streak: int = 0


class TeacherStudentActivityOut(BaseModel):
    id: str
    event_type: str
    title: str
    description: str | None = None
    occurred_at: str


class TeacherStudentNoteOut(BaseModel):
    id: int
    note_text: str
    created_at: str
    updated_at: str


class TeacherStudentNoteCreateIn(BaseModel):
    note_text: str = Field(min_length=1, max_length=2000)


class TeacherStudentNoteUpdateIn(BaseModel):
    note_text: str = Field(min_length=1, max_length=2000)


class TeacherStudentAnalyticsOut(BaseModel):
    completion_percent: int = 0
    average_score_percent: int = 0
    total_study_activity: int = 0
    active_streak: int = 0
    last_active_date: str | None = None


class TeacherStudentInsightOut(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    last_activity_title: str | None = None
    last_activity_at: str | None = None
    last_quiz_title: str | None = None
    last_quiz_score_percent: int | None = None
    last_quiz_at: str | None = None
    suggested_actions: list[str] = Field(default_factory=list)
    scope_subjects: list[str] = Field(default_factory=list)


class TeacherStudentLinkedParentOut(BaseModel):
    parent_id: int
    full_name: str
    email: str | None = None
    relationship_label: str | None = None


class TeacherStudentProfileOut(BaseModel):
    info: TeacherStudentInfoOut
    analytics: TeacherStudentAnalyticsOut
    learning: TeacherStudentLearningOut
    quiz_analytics: TeacherStudentQuizAnalyticsOut
    language: TeacherStudentLanguageOut | None = None
    activity_timeline: list[TeacherStudentActivityOut] = Field(default_factory=list)
    notes: list[TeacherStudentNoteOut] = Field(default_factory=list)
    gamification: GamificationProfileOut | None = None
    teacher_insight: TeacherStudentInsightOut | None = None
    linked_parents: list[TeacherStudentLinkedParentOut] = Field(default_factory=list)
    analytics_scope_label: str | None = None
