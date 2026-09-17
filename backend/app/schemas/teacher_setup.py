from pydantic import BaseModel, Field

from app.core.academic_grades import MIN_ACADEMIC_GRADE, MAX_ACADEMIC_GRADE


class TeacherSetupStatusOut(BaseModel):
    setup_complete: bool
    full_name: str | None = None
    display_name: str | None = None
    image_url: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    subject_ids: list[int] = Field(default_factory=list)
    grades: list[int] = Field(default_factory=list)


class TeacherProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    bio: str | None = Field(default=None, max_length=2000)


class TeacherTeachingUpdate(BaseModel):
    subject_ids: list[int] = Field(min_length=1)
    grades: list[int] = Field(min_length=1)


class TeacherCourseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=500)
    subject_id: int
    grade: int = Field(ge=MIN_ACADEMIC_GRADE, le=MAX_ACADEMIC_GRADE)
    price: float = Field(ge=0)


class TeacherSetupCompleteOut(BaseModel):
    ok: bool = True
    next_route: str = "/teacher/dashboard"
