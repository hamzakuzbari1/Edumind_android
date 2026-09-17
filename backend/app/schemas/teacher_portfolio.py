from pydantic import BaseModel, Field


class TeachingImpactOut(BaseModel):
    total_students_taught: int | None = None
    grade12_students_taught: int | None = None
    students_completed_subject: int | None = None
    students_excellent_grades: int | None = None
    years_teaching_subject: int | None = None
    highlights: list[str] = Field(default_factory=list)


class TeachingImpactUpdate(BaseModel):
    total_students_taught: int | None = Field(default=None, ge=0, le=1_000_000)
    grade12_students_taught: int | None = Field(default=None, ge=0, le=1_000_000)
    students_completed_subject: int | None = Field(default=None, ge=0, le=1_000_000)
    students_excellent_grades: int | None = Field(default=None, ge=0, le=1_000_000)
    years_teaching_subject: int | None = Field(default=None, ge=0, le=80)


class TeachingPhilosophyOut(BaseModel):
    teaching_style: str | None = None
    lesson_approach: str | None = None
    exam_preparation_strategy: str | None = None


class TeachingPhilosophyUpdate(BaseModel):
    teaching_style: str | None = Field(default=None, max_length=3000)
    lesson_approach: str | None = Field(default=None, max_length=3000)
    exam_preparation_strategy: str | None = Field(default=None, max_length=3000)


class TeacherWhyStudyPointOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    sort_order: int = 0


class TeacherWhyStudyPointCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int = Field(default=0, ge=0)


class TeacherWhyStudyPointUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = Field(default=None, ge=0)


class TeacherAcademicStatisticsOut(BaseModel):
    active_students: int = 0
    total_students: int = 0
    courses_published: int = 0
    lessons_published: int = 0
    average_lesson_completion_rate: float = 0.0
    average_quiz_score: float | None = None


class TeacherProfessionalDocumentOut(BaseModel):
    id: int
    title: str
    document_type: str
    file_url: str
    original_filename: str | None = None
    mime_type: str | None = None
    sort_order: int = 0


class TeacherProfessionalDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    document_type: str = Field(default="certificate", pattern="^(certificate|degree|training)$")
    sort_order: int = Field(default=0, ge=0)


class TeacherProfessionalDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    document_type: str | None = Field(default=None, pattern="^(certificate|degree|training)$")
    sort_order: int | None = Field(default=None, ge=0)


class TeacherPortfolioEditOut(BaseModel):
    teaching_impact: TeachingImpactOut
    teaching_philosophy: TeachingPhilosophyOut
    why_study_points: list[TeacherWhyStudyPointOut] = Field(default_factory=list)
    professional_documents: list[TeacherProfessionalDocumentOut] = Field(default_factory=list)
    academic_statistics: TeacherAcademicStatisticsOut
