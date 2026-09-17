"""Lesson completion progress schemas."""

from pydantic import BaseModel, Field


class RequirementCheckItemOut(BaseModel):
    key: str
    label: str
    met: bool = False
    required: bool = True


class LessonRequirementsOut(BaseModel):
    requires_video: bool = False
    requires_pdf: bool = False
    requires_quiz: bool = False
    video_threshold: float = 90.0
    pdf_threshold: float = 100.0
    quiz_score_threshold: float = 100.0
    video_met: bool = False
    pdf_met: bool = False
    quiz_submitted_met: bool = False
    quiz_score_met: bool = False
    quiz_met: bool = False


class LessonProgressOut(BaseModel):
    lesson_id: int
    lesson_title: str | None = None
    course_id: int | None = None
    video_progress_percent: float = 0
    pdf_progress_percent: float = 0
    pdf_opened: bool = False
    quiz_submitted: bool = False
    quiz_score_percent: float = 0
    is_completed: bool = False
    completed_at: str | None = None
    completion_type: str | None = None
    completion_percentage: float = 0
    completion_percent: int = 0
    requirements: LessonRequirementsOut
    checklist: list[RequirementCheckItemOut] = Field(default_factory=list)
    can_verify: bool = False
    lesson_type: str = "other"
    newly_completed: bool = False


class LessonProgressUpdateIn(BaseModel):
    video_percent: float | None = Field(None, ge=0, le=100)
    pdf_percent: float | None = Field(None, ge=0, le=100)
    pdf_opened: bool | None = None


class VerifyCompletionOut(BaseModel):
    success: bool
    message: str
    checklist: list[RequirementCheckItemOut] = Field(default_factory=list)
    progress: LessonProgressOut | None = None


class CourseLessonProgressSummaryOut(BaseModel):
    completed_count: int = 0
    pending_count: int = 0
    in_progress_count: int = 0
    completion_percent: int = 0
    completed_lesson_ids: list[int] = Field(default_factory=list)
    pending_lesson_ids: list[int] = Field(default_factory=list)
    in_progress_lesson_ids: list[int] = Field(default_factory=list)


class LessonCompletionStatsOut(BaseModel):
    completed_lessons: int = 0
    in_progress_lessons: int = 0
    pending_lessons: int = 0
    total_lessons: int = 0
    completion_rate: int = 0
    current_lesson_title: str | None = None


class ParentLessonProgressItemOut(BaseModel):
    lesson_id: int
    lesson_title: str
    course_id: int
    course_title: str = ""
    subject_name: str = ""
    status: str
    status_label: str
    status_icon: str = "pending"
    completion_percent: int = 0
    completion_quality: str = "none"
    is_verified: bool = False
    completed_at: str | None = None
    last_activity_at: str | None = None
    teacher_name: str | None = None
    lesson_type: str = "lesson"
    lesson_type_label: str = "درس"
    lesson_type_icon: str = "mdi-book-open-page-variant-outline"


class ParentCourseLessonProgressOut(BaseModel):
    course_id: int
    course_title: str
    subject_name: str = ""
    completed_count: int = 0
    in_progress_count: int = 0
    pending_count: int = 0
    total_lessons: int = 0
    progress_percent: int = 0
    lessons: list[ParentLessonProgressItemOut] = Field(default_factory=list)


class ParentLessonProgressSummaryOut(BaseModel):
    completed_lessons: int = 0
    in_progress_lessons: int = 0
    pending_lessons: int = 0
    total_lessons: int = 0
    completion_rate: int = 0
    current_lesson_title: str | None = None


class ParentLessonProgressOut(BaseModel):
    student_id: int
    courses: list[ParentCourseLessonProgressOut] = Field(default_factory=list)
    summary: ParentLessonProgressSummaryOut


class ParentLessonTimelineItemOut(BaseModel):
    date: str
    datetime: str | None = None
    label: str
    icon: str = "mdi-circle-small"


class ParentLessonDetailOut(BaseModel):
    lesson_id: int
    lesson_title: str
    course_id: int | None = None
    course_title: str = ""
    subject_name: str = ""
    teacher_name: str = ""
    video_progress_percent: float = 0
    video_last_watched_at: str | None = None
    pdf_progress_percent: float = 0
    pdf_total_pages: int | None = None
    pdf_pages_viewed: int | None = None
    pdf_opened: bool = False
    quiz_score_percent: float = 0
    quiz_attempt_count: int = 0
    quiz_last_attempt_at: str | None = None
    completion_status: str = ""
    completion_status_code: str = ""
    is_verified: bool = False
    verification_status: str = ""
    verification_status_label: str = ""
    completed_at: str | None = None
    started_at: str | None = None
    completion_type: str | None = None
    completion_percent: int = 0
    completion_quality: str = "none"
    checklist: list[RequirementCheckItemOut] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    requirements: dict = Field(default_factory=dict)
    timeline: list[ParentLessonTimelineItemOut] = Field(default_factory=list)
