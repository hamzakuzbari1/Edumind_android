from pydantic import BaseModel, Field


class LessonPublishStepOut(BaseModel):
    key: str
    label: str
    done: bool
    active: bool = False
    error: str | None = None


class LessonPublishOut(BaseModel):
    lesson_id: int
    course_id: int
    course_title: str
    title: str
    status: str
    has_video: bool = False
    has_pdf: bool = False
    ai_processing_scheduled: bool = False
    teacher_voice_ready: bool = False
    message: str


class LessonPublishStatusOut(BaseModel):
    lesson_id: int
    lesson_status: str
    lesson_error: str | None = None
    has_video: bool = False
    has_pdf: bool = False
    has_ai_chat: bool = False
    has_generated_quiz: bool = False
    ai_ready: bool = False
    teacher_voice_ready: bool = False
    steps: list[LessonPublishStepOut] = Field(default_factory=list)
    complete: bool = False
    ai_job_id: int | None = None
    ai_job_status: str | None = None
    ai_job_error: str | None = None
