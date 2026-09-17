"""Parent visibility into student subjects, courses, and assigned teachers."""

from pydantic import BaseModel, Field

from app.schemas.student_courses import StudentCourseTeacherProfileOut


class ParentSubjectCourseOut(BaseModel):
    subject_id: int
    subject_name: str
    course_id: int
    course_title: str
    teacher_user_id: int
    teacher_profile_id: int
    teacher_name: str
    teacher_image_url: str | None = None
    enrolled: bool = False
    subscription_status: str = "pending"
    progress_percent: int = 0
    lesson_count: int = 0
    completed_lesson_count: int = 0
    thread_id: int | None = None
    unread_count: int = 0


class ParentSubjectsTeachersOut(BaseModel):
    student_id: int
    student_name: str = ""
    grade: int | None = None
    grade_label: str = ""
    enrolled: list[ParentSubjectCourseOut] = Field(default_factory=list)
    available: list[ParentSubjectCourseOut] = Field(default_factory=list)
    enrolled_count: int = 0
    available_count: int = 0
    has_grade: bool = True


# Re-export for parent teacher-profile endpoint
ParentCourseTeacherProfileOut = StudentCourseTeacherProfileOut
