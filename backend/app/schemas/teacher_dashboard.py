from pydantic import BaseModel, Field


class TeacherKpiOut(BaseModel):
    id: str
    title: str
    value: str
    subtitle: str | None = None
    icon: str | None = None


class TeacherSubscriptionSummaryOut(BaseModel):
    active_subscribers: int = 0
    expiring_soon: int = 0
    expired_subscribers: int = 0


class TeacherOverviewOut(BaseModel):
    kpis: list[TeacherKpiOut] = Field(default_factory=list)
    recent_activity: list[str] = Field(default_factory=list)
    subscription_summary: TeacherSubscriptionSummaryOut = Field(
        default_factory=TeacherSubscriptionSummaryOut
    )


class TeacherCourseRowOut(BaseModel):
    course_id: int
    grade: int
    subject_id: int
    subject_name: str
    title: str
    price: float = 0
    thumbnail_url: str | None = None
    is_published: bool = True
    lesson_count: int = 0
    subscribed_students: int = 0
    completion_percent: int = 0
    avg_quiz_percent: int = 0
    most_viewed_lesson_title: str | None = None


class TeacherGradesOut(BaseModel):
    courses: list[TeacherCourseRowOut] = Field(default_factory=list)


class TeacherLessonRowOut(BaseModel):
    id: int
    course_id: int | None = None
    title: str
    content_type: str = "video"
    content_type_label: str = "فيديو"
    status: str = "processed"
    created_at: str | None = None
    completion_percent: int = 0


class TeacherStudentRowOut(BaseModel):
    student_id: int
    full_name: str
    subscription_status: str = "pending"
    activated_at: str | None = None
    expires_at: str | None = None
    days_until_expiry: int | None = None
    progress_percent: int = 0
    completed_lessons: int = 0
    in_progress_lessons: int = 0
    total_lessons: int = 0
    verified_completions: int = 0
    last_completion_at: str | None = None
    last_activity_at: str | None = None
    attendance_percent: int = 0
    avg_quiz_percent: int = 0


class TeacherCourseAnalyticsOut(BaseModel):
    subscribed_students: int = 0
    active_subscribers: int = 0
    expiring_soon: int = 0
    expired_subscribers: int = 0
    lesson_count: int = 0
    completion_percent: int = 0
    avg_quiz_percent: int = 0
    most_viewed_lesson_title: str | None = None


class TeacherCourseDetailOut(BaseModel):
    course_id: int
    grade: int
    subject_id: int
    subject_name: str
    title: str
    description: str | None = None
    price: float = 0
    thumbnail_url: str | None = None
    banner_url: str | None = None
    is_published: bool = True
    analytics: TeacherCourseAnalyticsOut = Field(default_factory=TeacherCourseAnalyticsOut)
    lessons: list[TeacherLessonRowOut] = Field(default_factory=list)
    students: list[TeacherStudentRowOut] = Field(default_factory=list)
