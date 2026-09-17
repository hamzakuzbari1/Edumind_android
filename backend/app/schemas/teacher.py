from pydantic import BaseModel, Field


class LessonCreateMeta(BaseModel):
    subject: str
    grade: str
    title: str | None = None


class LessonOut(BaseModel):
    id: int
    title: str
    subject: str
    grade: str
    status: str
    preview: str | None = None
    pdfUrl: str | None = None
    page_count: int | None = None
    created_at: str | None = None
    students: int = 0
    questions: int = 0

    model_config = {"from_attributes": True}


class ProcessResponse(BaseModel):
    lesson_id: int
    status: str
    message: str
