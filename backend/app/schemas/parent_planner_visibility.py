"""Parent planner visibility schemas."""

from pydantic import BaseModel, Field


class ParentPlannerTaskOut(BaseModel):
    id: int
    subject: str = ""
    task_name: str = ""
    planned_at: str | None = None
    completed_at: str | None = None
    status: str = "planned"
    status_label: str = ""
    status_icon: str = "pending"
    duration_minutes: int = 0
    is_overdue: bool = False


class ParentPlannerDayPlanOut(BaseModel):
    day_name: str
    date: str
    tasks: list[ParentPlannerTaskOut] = Field(default_factory=list)


class ParentPlannerCommitmentOut(BaseModel):
    adherence_rate: int = 0
    completed_count: int = 0
    total_due_count: int = 0
    missed_count: int = 0
    pending_count: int = 0
    overdue_count: int = 0


class ParentPlannerSubjectCommitmentOut(BaseModel):
    subject_name: str
    adherence_percent: int = 0
    completed_count: int = 0
    total_count: int = 0


class ParentPlannerConsistencyOut(BaseModel):
    active_days: int = 0
    total_days: int = 7
    label: str = ""


class ParentPlannerVisibilityOut(BaseModel):
    summary: str = ""
    plan_active: bool = False
    today_plan: list[ParentPlannerTaskOut] = Field(default_factory=list)
    weekly_plan: list[ParentPlannerDayPlanOut] = Field(default_factory=list)
    upcoming_tasks: list[ParentPlannerTaskOut] = Field(default_factory=list)
    completed_tasks: list[ParentPlannerTaskOut] = Field(default_factory=list)
    missed_tasks: list[ParentPlannerTaskOut] = Field(default_factory=list)
    overdue_tasks: list[ParentPlannerTaskOut] = Field(default_factory=list)
    task_timeline: list[ParentPlannerTaskOut] = Field(default_factory=list)
    commitment: ParentPlannerCommitmentOut = Field(default_factory=ParentPlannerCommitmentOut)
    subject_breakdown: list[ParentPlannerSubjectCommitmentOut] = Field(default_factory=list)
    weekly_consistency: ParentPlannerConsistencyOut = Field(default_factory=ParentPlannerConsistencyOut)
    streak: dict = Field(default_factory=dict)
    recommendations: list[dict] = Field(default_factory=list)
    subject_analytics: list[dict] = Field(default_factory=list)
    # Legacy fields for dashboard compatibility
    upcoming: list[dict] = Field(default_factory=list)
    weekly_plan_legacy: list[dict] = Field(default_factory=list)
    plan_stats: dict = Field(default_factory=dict)
    completed_total: int = 0
