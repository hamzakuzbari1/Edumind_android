from datetime import date, datetime

from pydantic import BaseModel, Field


class AttendanceRecordOut(BaseModel):
    id: int
    student_id: int
    date: date
    status: str
    study_minutes: int
    consistency_score: int
    notes: str | None = None
    day_label: str = ""
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AttendanceDayCellOut(BaseModel):
    date: str
    day_label: str
    status: str
    study_minutes: int
    consistency_score: int
    active: bool = False


class AttendanceWeekBarOut(BaseModel):
    week_label: str
    consistency: int
    present_days: int
    total_days: int = 7


class AttendanceMonthWeekOut(BaseModel):
    week_index: int
    label: str
    consistency: int
    present: int
    absent: int
    partial: int


class AttendanceAlertOut(BaseModel):
    type: str
    text: str


class AttendanceSummaryOut(BaseModel):
    attendance_percentage: int = 0
    weekly_consistency: int = 0
    streak_days: int = 0
    inactive_days: int = 0
    completed_sessions: int = 0
    missed_sessions: int = 0
    partial_days: int = 0
    total_study_minutes_week: int = 0
    weekly_calendar: list[AttendanceDayCellOut] = Field(default_factory=list)
    monthly_overview: list[AttendanceMonthWeekOut] = Field(default_factory=list)
    consistency_bars: list[AttendanceWeekBarOut] = Field(default_factory=list)
    alerts: list[AttendanceAlertOut] = Field(default_factory=list)
    ai_insights: list[str] = Field(default_factory=list)
    recent_records: list[AttendanceRecordOut] = Field(default_factory=list)
