"""Parent executive summary — AI insights page payload."""

from pydantic import BaseModel, Field

from app.schemas.activity import ParentInsightOut


class WeeklySnapshotOut(BaseModel):
    lessons_completed: int = 0
    study_hours: float = 0
    average_quiz_score: int | None = None
    planner_adherence_percent: int | None = None
    missed_planner_tasks: int = 0
    most_active_subject: str | None = None
    weakest_subject: str | None = None
    strongest_subject: str | None = None


class PeriodComparisonMetricOut(BaseModel):
    label: str
    current_value: float
    previous_value: float
    change_percent: float | None = None
    unit: str = ""


class PeriodComparisonOut(BaseModel):
    period_label: str = "هذا الأسبوع مقابل الأسبوع السابق"
    study_time: PeriodComparisonMetricOut | None = None
    lesson_completion: PeriodComparisonMetricOut | None = None
    quiz_performance: PeriodComparisonMetricOut | None = None
    planner_adherence: PeriodComparisonMetricOut | None = None


class StudyTimeAveragesOut(BaseModel):
    daily_hours: float = 0
    weekly_hours: float = 0
    monthly_hours: float = 0
    daily_trend_percent: float | None = None
    weekly_trend_percent: float | None = None
    monthly_trend_percent: float | None = None


class SubjectAnalysisOut(BaseModel):
    subject: str
    reasons: list[str] = Field(default_factory=list)
    average_score: int | None = None
    study_minutes: int = 0
    engagement_rank: int | None = None


class StudyBehaviorOut(BaseModel):
    average_daily_study_hours: float = 0
    preferred_study_hours_label: str | None = None
    preferred_study_hours_start: int | None = None
    preferred_study_hours_end: int | None = None
    consistency_level: str = "unknown"
    consistency_label: str = ""
    active_days_this_week: int = 0
    total_days_this_week: int = 7


class NotificationSignalsOut(BaseModel):
    recent_alerts_count: int = 0
    unread_count: int = 0
    has_inactivity_alert: bool = False
    has_low_score_alert: bool = False
    has_planner_alert: bool = False


class ParentExecutiveSummaryOut(BaseModel):
    student_name: str = ""
    grade_label: str = ""
    academic_status_label: str = ""
    weekly_snapshot: WeeklySnapshotOut = Field(default_factory=WeeklySnapshotOut)
    period_comparison: PeriodComparisonOut = Field(default_factory=PeriodComparisonOut)
    study_time_averages: StudyTimeAveragesOut = Field(default_factory=StudyTimeAveragesOut)
    study_behavior: StudyBehaviorOut = Field(default_factory=StudyBehaviorOut)
    strength_analysis: SubjectAnalysisOut | None = None
    weakness_analysis: SubjectAnalysisOut | None = None
    risk_alerts: list[ParentInsightOut] = Field(default_factory=list)
    recommendations: list[ParentInsightOut] = Field(default_factory=list)
    summary_lines: list[str] = Field(default_factory=list)
    planner_analytics: dict = Field(default_factory=dict)
    notification_signals: NotificationSignalsOut = Field(default_factory=NotificationSignalsOut)
    latest_insight: ParentInsightOut | None = None
    has_data: bool = False
