from pydantic import BaseModel, Field

from app.schemas.activity import ActivityEventOut, ParentInsightOut
from app.schemas.language_analytics import ParentLanguageAnalyticsSummaryOut
from app.schemas.language_certificate import LanguageCertificateSummaryOut


class LinkedChildOut(BaseModel):
    id: int
    name: str
    email: str
    grade: int | None = None
    grade_label: str = ""
    academic_status: str = "inactive"
    academic_status_label: str = ""
    last_activity_at: str | None = None


class QuizResultItem(BaseModel):
    id: int | str
    subject: str
    lesson_title: str = ""
    score: int
    trend: int | None = None
    date: str | None = None
    relative: str = ""
    demo: bool = False


class QuizTrackingOut(BaseModel):
    recent: list[QuizResultItem] = Field(default_factory=list)
    chart: list[dict] = Field(default_factory=list)
    weak_subjects: list[str] = Field(default_factory=list)
    best_subject: dict | None = None
    average_score: int = 0
    ai_comments: list[str] = Field(default_factory=list)


class AttendanceOut(BaseModel):
    attendance_percentage: int = 0
    weekly_consistency: int = 0
    streak_days: int = 0
    inactive_days: int = 0
    completed_sessions: int = 0
    missed_sessions: int = 0
    partial_days: int = 0
    total_study_minutes_week: int = 0
    weekly_calendar: list[dict] = Field(default_factory=list)
    monthly_overview: list[dict] = Field(default_factory=list)
    consistency_bars: list[dict] = Field(default_factory=list)
    alerts: list[dict] = Field(default_factory=list)
    ai_insights: list[str] = Field(default_factory=list)
    recent_records: list[dict] = Field(default_factory=list)
    daily: list[dict] = Field(default_factory=list)


from app.schemas.gamification import GamificationProfileOut
from app.schemas.lesson_completion import ParentLessonProgressOut
from app.schemas.parent_planner_visibility import ParentPlannerVisibilityOut


class PlannerProgressOut(ParentPlannerVisibilityOut):
    """Alias — planner payload for parent dashboard and planner page."""


class CourseProgressOut(BaseModel):
    course_id: int
    course_title: str
    subject_name: str = ""
    average_score: float | None = None
    attendance_percentage: float | None = None
    completion_percentage: float | None = None
    updated_at: str | None = None


class StudentSubscriptionStatusOut(BaseModel):
    course_id: int
    course_title: str
    subject_name: str = ""
    subscription_status: str = "pending"
    activated_at: str | None = None
    expires_at: str | None = None
    days_until_expiry: int | None = None


class LanguagePlacementSummaryOut(BaseModel):
    language_code: str = "en"
    reading_level: str | None = None
    listening_level: str | None = None
    writing_level: str | None = None
    speaking_level: str | None = None
    overall_level: str | None = None
    overall_calculation_method: str = "bottleneck"
    skill_growth: dict | None = None
    vocabulary_count: int = 0
    vocabulary_learned: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    completed_activities: int = 0
    writing_completed: int = 0
    speaking_completed: int = 0
    latest_certificate: LanguageCertificateSummaryOut | None = None
    language_analytics_summary: ParentLanguageAnalyticsSummaryOut | None = None


class ParentDashboardOut(BaseModel):
    child: LinkedChildOut
    activity: list[ActivityEventOut]
    insights: list[ParentInsightOut]
    stats: dict
    quiz: QuizTrackingOut
    attendance: AttendanceOut
    planner: PlannerProgressOut
    course_progress: list[CourseProgressOut] = Field(default_factory=list)
    subscriptions: list[StudentSubscriptionStatusOut] = Field(default_factory=list)
    language_placement: LanguagePlacementSummaryOut | None = None
    gamification: GamificationProfileOut | None = None
    academic_intelligence: "ParentAcademicIntelligenceOut | None" = None
    lesson_progress: ParentLessonProgressOut | None = None


class SubjectAcademicOut(BaseModel):
    subject_name: str
    course_id: int
    course_title: str = ""
    quiz_average: float | None = None
    exam_average: float | None = None
    completion_rate: float | None = None
    quiz_attempts: int = 0
    exam_attempts: int = 0
    completed_lessons: int = 0
    total_lessons: int = 0
    composite_score: float | None = None
    performance_indicator: str | None = None
    performance_label: str = ""
    assignments_available: bool = False


class SubjectComparisonOut(BaseModel):
    subject_name: str
    quiz_average: float | None = None
    exam_average: float | None = None
    completion_rate: float | None = None
    composite_score: float | None = None


class SubjectHighlightOut(BaseModel):
    subject_name: str
    course_id: int
    composite_score: float | None = None


class AcademicDataSourcesOut(BaseModel):
    quiz_attempts: int = 0
    exam_attempts: int = 0
    lesson_completions: int = 0
    assignments_available: bool = False


class ParentAcademicIntelligenceOut(BaseModel):
    overall_average: float | None = None
    performance_indicator: str | None = None
    performance_label: str = ""
    best_subject: SubjectHighlightOut | None = None
    weakest_subject: SubjectHighlightOut | None = None
    subjects: list[SubjectAcademicOut] = Field(default_factory=list)
    subject_comparison: list[SubjectComparisonOut] = Field(default_factory=list)
    data_sources: AcademicDataSourcesOut = Field(default_factory=AcademicDataSourcesOut)
    has_data: bool = False
    summary: str = ""
