"""Parent attendance analytics API schemas."""

from pydantic import BaseModel


class StudyTimeAveragesOut(BaseModel):
    daily_hours: float = 0
    weekly_hours: float = 0
    monthly_hours: float = 0
    daily_trend_percent: float | None = None
    weekly_trend_percent: float | None = None
    monthly_trend_percent: float | None = None


class StudyTimeOverviewOut(BaseModel):
    today_minutes: int = 0
    week_minutes: int = 0
    month_minutes: int = 0
    last_activity_at: str | None = None
    week_comparison_percent: float | None = None
    month_comparison_percent: float | None = None
    averages: StudyTimeAveragesOut = StudyTimeAveragesOut()


class DailyStudyOut(BaseModel):
    date: str
    day_label: str
    study_minutes: int = 0


class WeeklyAnalyticsOut(BaseModel):
    period_label: str
    total_minutes: int = 0
    daily_average_minutes: float = 0
    most_active_day: DailyStudyOut | None = None
    least_active_day: DailyStudyOut | None = None
    comparison_percent: float | None = None
    active_days_count: int = 0


class MonthlyWeekBucketOut(BaseModel):
    week_index: int
    study_minutes: int = 0


class MonthlyAnalyticsOut(BaseModel):
    period_label: str
    total_minutes: int = 0
    weekly_average_minutes: float = 0
    comparison_percent: float | None = None
    trend: str = "flat"
    weeks: list[MonthlyWeekBucketOut] = []
    daily_breakdown: list[DailyStudyOut] = []


class LoginHistoryRowOut(BaseModel):
    id: int
    date: str | None = None
    day_label: str | None = None
    login_at: str | None = None
    logout_at: str | None = None
    logout_reason: str | None = None
    active_minutes: int = 0
    is_open: bool = False


class ParentAttendanceAnalyticsOut(BaseModel):
    overview: StudyTimeOverviewOut
    week_offset: int = 0
    month_offset: int = 0
    daily_breakdown: list[DailyStudyOut] = []
    weekly_analytics: WeeklyAnalyticsOut
    monthly_analytics: MonthlyAnalyticsOut
    login_history: list[LoginHistoryRowOut] = []
    data_source: dict[str, str] = {}
