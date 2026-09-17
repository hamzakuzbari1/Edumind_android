from pydantic import BaseModel, Field

from app.core.academic_grades import MIN_ACADEMIC_GRADE, MAX_ACADEMIC_GRADE
from app.schemas.catalog import CoursePreviewOut, SubjectOut, TeacherCardOut


class OnboardingStatusOut(BaseModel):
    step: str
    grade: int | None = None
    onboarding_complete: bool = False
    needs_payment: bool = False
    payment_complete: bool = False
    selected_subject_ids: list[int] = Field(default_factory=list)
    teacher_choices: list[dict] = Field(default_factory=list)


class GradeUpdate(BaseModel):
    grade: int = Field(ge=MIN_ACADEMIC_GRADE, le=MAX_ACADEMIC_GRADE)


class SubjectsUpdate(BaseModel):
    subject_ids: list[int] = Field(min_length=1)


class TeacherChoiceItem(BaseModel):
    subject_id: int
    teacher_profile_id: int


class TeachersUpdate(BaseModel):
    choices: list[TeacherChoiceItem] = Field(min_length=1)


class OnboardingCompleteOut(BaseModel):
    ok: bool = True
    next_route: str = "/student/payment"
    checkout_preview: list[CoursePreviewOut] = Field(default_factory=list)
