"""Parent visibility schema for المخطط والالتزام (daily routine)."""

from pydantic import BaseModel, Field


class ParentRoutineExamOut(BaseModel):
    subject: str
    days_left: int


class ParentRoutineSlotOut(BaseModel):
    start: str
    end: str
    title: str
    subject: str | None = None
    status: str = "planned"  # "completed" | "missed" | "planned"


class ParentRoutineDayOut(BaseModel):
    index: int
    label: str
    status: str = "no_plan"  # "completed" | "partial" | "missed" | "no_plan"
    slots: list[ParentRoutineSlotOut] = Field(default_factory=list)


class ParentRoutineVisibilityOut(BaseModel):
    onboarding_complete: bool = False
    weekly_commitment_percent: int = 0
    days: list[ParentRoutineDayOut] = Field(default_factory=list)
    today_label: str = ""
    today_slots: list[ParentRoutineSlotOut] = Field(default_factory=list)
    upcoming_exams: list[ParentRoutineExamOut] = Field(default_factory=list)
    weak_subjects: list[str] = Field(default_factory=list)
