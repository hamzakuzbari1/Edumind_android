from datetime import datetime

from pydantic import BaseModel, Field


class PlannerProfileOut(BaseModel):
    preferred_period: str = "evening"
    school_start: str = "08:00"
    school_end: str = "14:00"
    max_daily_minutes: int = 120
    weak_subjects: list[str] = Field(default_factory=list)
    memory: dict = Field(default_factory=dict)


class LifeEventOut(BaseModel):
    id: int
    title: str
    event_type: str
    day_of_week: int | None = None
    event_date: datetime | None = None
    start_time: str | None = None
    duration_minutes: int = 60
    is_blocking: bool = True
    subject: str | None = None


class ScheduleSlotOut(BaseModel):
    id: int
    subject: str
    scheduled_at: datetime
    duration_minutes: int
    priority: int
    status: str
    reasoning: str | None = None
    priority_tier: str | None = None
    priority_label: str | None = None
    priority_icon: str | None = None
    task_label: str | None = None


class WeeklyPlanDayOut(BaseModel):
    day_name: str
    day_offset: int = 0
    tasks: list[ScheduleSlotOut] = Field(default_factory=list)


class SubjectAnalyticsOut(BaseModel):
    subject_name: str
    course_id: int | None = None
    average_score: int = 0
    completion_percent: int = 0
    missed_lessons: int = 0
    failed_quizzes: int = 0
    total_lessons: int = 0
    completed_lessons: int = 0
    strength_level: str = "medium"
    strength_label: str = "متوسط"


class PlannerRecommendationOut(BaseModel):
    text: str
    priority_tier: str = "medium"
    priority_label: str = "أولوية متوسطة"
    priority_icon: str = "⚠️"
    subject: str | None = None


class StudyStreakOut(BaseModel):
    current_streak_days: int = 0
    longest_streak_days: int = 0
    task_streak_days: int = 0
    last_study_date: str | None = None


class PlannerDashboardSnapshotOut(BaseModel):
    today_tasks: list[ScheduleSlotOut] = Field(default_factory=list)
    today_label: str = ""
    current_priority: dict | None = None
    streak: StudyStreakOut = Field(default_factory=StudyStreakOut)
    next_task: ScheduleSlotOut | None = None
    streak_display: str = ""


class PlannerPlanStatsOut(BaseModel):
    planned_count: int = 0
    completed_count: int = 0
    missed_count: int = 0


class PlannerChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class PlannerStateOut(BaseModel):
    profile: PlannerProfileOut
    life_events: list[LifeEventOut]
    schedule: list[ScheduleSlotOut]
    chat_history: list[PlannerChatMessageOut]
    reasoning: list[str] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    weekly_plan: list[WeeklyPlanDayOut] = Field(default_factory=list)
    subject_analytics: list[SubjectAnalyticsOut] = Field(default_factory=list)
    recommendations: list[PlannerRecommendationOut] = Field(default_factory=list)
    streak: StudyStreakOut = Field(default_factory=StudyStreakOut)
    dashboard_snapshot: PlannerDashboardSnapshotOut = Field(default_factory=PlannerDashboardSnapshotOut)
    plan_stats: PlannerPlanStatsOut = Field(default_factory=PlannerPlanStatsOut)


class PlannerVisibilityOut(BaseModel):
    weekly_plan: list[WeeklyPlanDayOut] = Field(default_factory=list)
    subject_analytics: list[SubjectAnalyticsOut] = Field(default_factory=list)
    recommendations: list[PlannerRecommendationOut] = Field(default_factory=list)
    streak: StudyStreakOut = Field(default_factory=StudyStreakOut)
    plan_stats: PlannerPlanStatsOut = Field(default_factory=PlannerPlanStatsOut)
    upcoming: list[ScheduleSlotOut] = Field(default_factory=list)
    completed_tasks: list[ScheduleSlotOut] = Field(default_factory=list)
    missed_tasks: list[ScheduleSlotOut] = Field(default_factory=list)
    summary: str = ""


class PlannerChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class PlannerChatResponse(BaseModel):
    reply: str
    extracted_events: list[dict] = Field(default_factory=list)
    schedule: list[ScheduleSlotOut] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    profile: PlannerProfileOut | None = None
    life_events: list[LifeEventOut] = Field(default_factory=list)
    chat_history: list[PlannerChatMessageOut] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    weekly_plan: list[WeeklyPlanDayOut] = Field(default_factory=list)
    subject_analytics: list[SubjectAnalyticsOut] = Field(default_factory=list)
    recommendations: list[PlannerRecommendationOut] = Field(default_factory=list)
    streak: StudyStreakOut = Field(default_factory=StudyStreakOut)
    dashboard_snapshot: PlannerDashboardSnapshotOut = Field(default_factory=PlannerDashboardSnapshotOut)
    plan_stats: PlannerPlanStatsOut = Field(default_factory=PlannerPlanStatsOut)


class CompleteSessionRequest(BaseModel):
    slot_id: int
