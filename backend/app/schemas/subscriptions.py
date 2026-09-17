from pydantic import BaseModel, Field

from app.schemas.student_courses import StudentCourseCardOut


class SubscriptionCourseOut(StudentCourseCardOut):
    subscription_benefits: str = ""
    video_count: int = 0
    pdf_count: int = 0
    homework_count: int = 0
    ai_lesson_count: int = 0


class SubscriptionsCatalogOut(BaseModel):
    grade: int | None = None
    courses: list[SubscriptionCourseOut] = Field(default_factory=list)
    unlocked_count: int = 0
    available_count: int = 0


class SubscribeCourseRequest(BaseModel):
    course_id: int
    method: str = "card"


class SubscribeCourseOut(BaseModel):
    ok: bool = True
    course_id: int
    reference: str
    unlocked: bool = True
