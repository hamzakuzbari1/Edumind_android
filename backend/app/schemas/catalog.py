from pydantic import BaseModel, Field


class GradeOut(BaseModel):
    value: int
    label_ar: str


class SubjectOut(BaseModel):
    id: int
    name_ar: str
    slug: str
    grade: int


class TeacherCardOut(BaseModel):
    id: int
    full_name: str
    image_url: str | None
    bio: str | None
    rating: float
    student_count: int
    subject_id: int
    subject_name: str


class CoursePreviewOut(BaseModel):
    id: int
    title: str
    subject_name: str
    teacher_name: str
    teacher_image_url: str | None
    summary: str = ""
    grade: int
    price: float
    currency: str
