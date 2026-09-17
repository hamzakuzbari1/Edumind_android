from pydantic import BaseModel, Field

from app.schemas.teacher_portfolio import (
    TeacherAcademicStatisticsOut,
    TeacherProfessionalDocumentOut,
    TeacherWhyStudyPointOut,
    TeachingImpactOut,
    TeachingPhilosophyOut,
)
from app.schemas.teacher_profile_cv import (
    TeacherAchievementOut,
    TeacherQualificationOut,
    TeacherTeachingExperienceOut,
)


class CourseLessonOut(BaseModel):
    id: int
    unit_id: int | None = None
    unit_title: str | None = None
    title: str
    description: str | None = None
    video_url: str | None = None
    pdf_url: str | None = None
    homework_url: str | None = None
    sort_order: int = 0
    lesson_type: str = "video"
    lesson_type_label: str = "فيديو"
    status: str | None = None
    completed: bool = False
    created_at: str | None = None
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
    completion_percent: int = 0
    video_progress_percent: float = 0
    pdf_progress_percent: float = 0


class StudentCourseUnitOut(BaseModel):
    id: int | None = None
    title: str
    description: str | None = None
    sort_order: int = 0
    lesson_count: int = 0
    completed_lesson_count: int = 0
    progress_percent: int = 0
    lessons: list[CourseLessonOut] = Field(default_factory=list)


class StudentCourseResumeLessonOut(BaseModel):
    course_id: int
    lesson_id: int
    unit_id: int | None = None
    unit_title: str | None = None
    title: str
    sort_order: int = 0
    status: str = "pending"
    completion_percent: int = 0


class StudentLessonStatusOut(BaseModel):
    lesson_id: int
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


class StudentCourseCardOut(BaseModel):
    id: int
    title: str
    subject_name: str
    teacher_name: str
    teacher_image_url: str | None = None
    avatar_url: str | None = None
    grade: int
    price: float
    currency: str = "SYP"
    unlocked: bool
    subscription_status: str = "pending"
    access_status: str | None = None
    access_source: str | None = None
    enrollment_status: str | None = None
    activated_at: str | None = None
    expires_at: str | None = None
    days_until_expiry: int | None = None
    lock_reason: str | None = None
    progress_percent: int = 0
    lesson_count: int = 0
    completed_lesson_count: int = 0


class StudentCourseDetailOut(StudentCourseCardOut):
    description: str | None = None
    teacher_user_id: int | None = None
    teacher_profile_id: int | None = None
    has_linked_parent: bool = False
    existing_message_thread_id: int | None = None
    lessons: list[CourseLessonOut] = Field(default_factory=list)
    units: list[StudentCourseUnitOut] = Field(default_factory=list)
    resume_lesson: StudentCourseResumeLessonOut | None = None


class StudentCourseTeacherProfileOut(BaseModel):
    teacher_user_id: int
    teacher_profile_id: int
    full_name: str
    image_url: str | None = None
    bio: str | None = None
    rating: float = 0.0
    student_count: int = 0
    subject_name: str
    grade: int
    courses: list[str] = Field(default_factory=list)
    qualifications: list[TeacherQualificationOut] = Field(default_factory=list)
    teaching_experiences: list[TeacherTeachingExperienceOut] = Field(default_factory=list)
    achievements: list[TeacherAchievementOut] = Field(default_factory=list)
    teaching_impact: TeachingImpactOut | None = None
    teaching_philosophy: TeachingPhilosophyOut | None = None
    why_study_points: list[TeacherWhyStudyPointOut] = Field(default_factory=list)
    academic_statistics: TeacherAcademicStatisticsOut | None = None
    professional_documents: list[TeacherProfessionalDocumentOut] = Field(default_factory=list)


from app.schemas.gamification import GamificationProfileOut


class StudentDashboardOut(BaseModel):
    grade: int | None = None
    courses: list[StudentCourseCardOut] = Field(default_factory=list)
    unlocked_count: int = 0
    locked_count: int = 0
    gamification: GamificationProfileOut | None = None
    lesson_completion: "LessonCompletionStatsOut | None" = None


from app.schemas.lesson_completion import LessonCompletionStatsOut  # noqa: E402

StudentDashboardOut.model_rebuild()
