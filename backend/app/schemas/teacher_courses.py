from pydantic import BaseModel, Field

from app.core.academic_grades import MIN_ACADEMIC_GRADE, MAX_ACADEMIC_GRADE


class SubjectOptionOut(BaseModel):
    id: int
    name_ar: str
    grade: int


class TeacherCourseFormContextOut(BaseModel):
    grades: list[int] = Field(default_factory=list)
    subjects: list[SubjectOptionOut] = Field(default_factory=list)


class TeacherCourseOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    subject_name: str
    subject_id: int
    grade: int
    price: float
    currency: str = "SYP"
    thumbnail_url: str | None = None
    banner_url: str | None = None
    is_published: bool = True
    lesson_count: int = 0


class TeacherCourseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=500)
    description: str | None = None
    subject_id: int
    grade: int = Field(ge=MIN_ACADEMIC_GRADE, le=MAX_ACADEMIC_GRADE)
    price: float = Field(default=0, ge=0)
    currency: str = "SYP"
    is_published: bool = True


class TeacherCourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=500)
    description: str | None = None
    subject_id: int | None = None
    price: float | None = Field(default=None, ge=0)
    is_published: bool | None = None


class LessonAssetOut(BaseModel):
    asset_type: str
    url: str | None = None
    original_filename: str | None = None


class TeacherCourseLessonOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    video_url: str | None = None
    pdf_url: str | None = None
    homework_url: str | None = None
    audio_url: str | None = None
    assets: list[LessonAssetOut] = Field(default_factory=list)
    has_video: bool = False
    has_pdf: bool = False
    has_audio: bool = False
    sort_order: int = 0
    status: str
    is_visible: bool = True


class TeacherLessonPreviewOut(TeacherCourseLessonOut):
    course_id: int
    course_title: str | None = None
    subject_name: str | None = None
    grade: int | None = None
    content_type: str = "video"
    content_type_label: str = "فيديو"
    preview: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    error_message: str | None = None
    page_count: int | None = None
    completion_percent: int = 0
    needs_reprocessing: bool = False


class TeacherLessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=500)
    description: str | None = None
    is_visible: bool | None = None
    lesson_takeaways: list[str] | None = Field(
        default=None,
        description="Optional teacher-authored learning takeaways (3–5 short sentences)",
    )
    lesson_concepts: list[str] | None = Field(
        default=None,
        description="Optional teacher-authored key concepts (3–5 items)",
    )


class TeacherLessonContentUpdate(BaseModel):
    """Flags for multipart lesson content update (files sent separately)."""
    title: str = Field(min_length=2, max_length=500)
    description: str | None = None
    is_visible: bool = True
    remove_video: bool = False
    remove_pdf: bool = False
    remove_audio: bool = False
