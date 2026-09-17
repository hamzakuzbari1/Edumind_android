from pydantic import BaseModel, Field


class ParentLinkRequest(BaseModel):
    link_code: str = Field(min_length=6, max_length=16)


class StudentLinkCodeOut(BaseModel):
    link_code: str


class LinkedStudentOut(BaseModel):
    id: int
    name: str
    email: str
    grade: int | None = None
    grade_label: str = ""
    academic_status: str = "inactive"
    academic_status_label: str = ""
    last_activity_at: str | None = None

    model_config = {"from_attributes": True}
