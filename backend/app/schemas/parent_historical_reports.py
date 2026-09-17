"""Parent historical reports — period-scoped analytics from real platform data."""

from pydantic import BaseModel, Field


class ReportMetricComparisonOut(BaseModel):
    label: str
    current_value: float
    previous_value: float
    change_percent: float | None = None
    unit: str = ""


class ReportPeriodComparisonOut(BaseModel):
    period_label: str = ""
    previous_period_label: str = ""
    study_time: ReportMetricComparisonOut | None = None
    grades: ReportMetricComparisonOut | None = None
    lesson_completion: ReportMetricComparisonOut | None = None
    planner_adherence: ReportMetricComparisonOut | None = None


class ReportTrendPointOut(BaseModel):
    label: str
    date: str | None = None
    value: float
    secondary_value: float | None = None


class ReportLessonHistoryOut(BaseModel):
    weekly: list[ReportTrendPointOut] = Field(default_factory=list)
    monthly: list[ReportTrendPointOut] = Field(default_factory=list)
    total_in_period: int = 0


class ReportAttendanceHistoryOut(BaseModel):
    login_sessions: list[dict] = Field(default_factory=list)
    daily_study_trend: list[ReportTrendPointOut] = Field(default_factory=list)
    total_study_hours: float = 0
    total_sessions: int = 0


class ReportPlannerHistoryOut(BaseModel):
    adherence_trend: list[ReportTrendPointOut] = Field(default_factory=list)
    missed_tasks_trend: list[ReportTrendPointOut] = Field(default_factory=list)
    average_adherence: float = 0
    total_missed: int = 0


class ParentHistoricalReportOut(BaseModel):
    student_name: str = ""
    grade_label: str = ""
    period: str = "this_week"
    period_label: str = ""
    start_date: str = ""
    end_date: str = ""
    comparison: ReportPeriodComparisonOut = Field(default_factory=ReportPeriodComparisonOut)
    lesson_history: ReportLessonHistoryOut = Field(default_factory=ReportLessonHistoryOut)
    attendance_history: ReportAttendanceHistoryOut = Field(default_factory=ReportAttendanceHistoryOut)
    planner_history: ReportPlannerHistoryOut = Field(default_factory=ReportPlannerHistoryOut)
    has_data: bool = False
