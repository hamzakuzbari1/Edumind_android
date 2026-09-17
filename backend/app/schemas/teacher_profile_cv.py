from pydantic import BaseModel, Field


class TeacherQualificationOut(BaseModel):
    id: int
    title: str
    institution: str | None = None
    year: int | None = None
    description: str | None = None
    sort_order: int = 0


class TeacherQualificationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    institution: str | None = Field(default=None, max_length=255)
    year: int | None = Field(default=None, ge=1950, le=2100)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int = Field(default=0, ge=0)


class TeacherQualificationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    institution: str | None = Field(default=None, max_length=255)
    year: int | None = Field(default=None, ge=1950, le=2100)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = Field(default=None, ge=0)


class TeacherTeachingExperienceOut(BaseModel):
    id: int
    title: str
    organization: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    description: str | None = None
    sort_order: int = 0


class TeacherTeachingExperienceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    year_from: int | None = Field(default=None, ge=1950, le=2100)
    year_to: int | None = Field(default=None, ge=1950, le=2100)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int = Field(default=0, ge=0)


class TeacherTeachingExperienceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    year_from: int | None = Field(default=None, ge=1950, le=2100)
    year_to: int | None = Field(default=None, ge=1950, le=2100)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = Field(default=None, ge=0)


class TeacherAchievementOut(BaseModel):
    id: int
    title: str
    year: int | None = None
    description: str | None = None
    sort_order: int = 0
    is_pinned: bool = False


class TeacherAchievementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    year: int | None = Field(default=None, ge=1950, le=2100)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int = Field(default=0, ge=0)
    is_pinned: bool = False


class TeacherAchievementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    year: int | None = Field(default=None, ge=1950, le=2100)
    description: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = Field(default=None, ge=0)
    is_pinned: bool | None = None


class TeacherProfileCvOut(BaseModel):
    qualifications: list[TeacherQualificationOut] = Field(default_factory=list)
    teaching_experiences: list[TeacherTeachingExperienceOut] = Field(default_factory=list)
    achievements: list[TeacherAchievementOut] = Field(default_factory=list)
