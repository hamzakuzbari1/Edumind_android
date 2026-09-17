"""Pydantic schemas for language analytics dashboard and achievements (Phase 7.8)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LanguageAchievementItemOut(BaseModel):
    key: str
    icon: str
    title_ar: str
    title_en: str
    description_ar: str
    category: str
    earned: bool = False
    unlocked_at: datetime | None = None


class LanguageAchievementsOut(BaseModel):
    achievements: list[LanguageAchievementItemOut] = Field(default_factory=list)
    earned_count: int = 0
    total_count: int = 0


class LanguageImprovementTrendOut(BaseModel):
    recent_week_average: float | None = None
    prior_week_average: float | None = None
    delta: float | None = None
    direction: str = "stable"
    direction_ar: str = "مستقر"


class LanguageStatisticsOut(BaseModel):
    total_conversations: int = 0
    total_speaking_submissions: int = 0
    total_writing_submissions: int = 0
    total_study_minutes: int = 0
    total_study_seconds: int = 0
    completed_objectives: int = 0
    mastered_objectives: int = 0
    objectives_total: int = 0
    scenarios_completed: int = 0


class LanguageScenarioProgressOut(BaseModel):
    scenario_key: str
    scenario_id: int | None = None
    status: str = "not_started"
    completion_count: int = 0
    best_score: int = 0
    best_scores: dict = Field(default_factory=dict)
    last_played_at: datetime | None = None
    first_completed_at: datetime | None = None
    mastery_label_ar: str = ""


class LanguageSkillRadarOut(BaseModel):
    skill: str
    label_ar: str
    score: int = 0


class LanguageDailyMissionOut(BaseModel):
    completed: int = 0
    total: int = 0
    percent: int = 0
    recommendation: str | None = None
    detail_ar: str | None = None


class LanguageAnalyticsDashboardOut(BaseModel):
    current_cefr_level: str | None = None
    adaptive_recommendation: str | None = None
    adaptive_recommendation_ar: str | None = None
    overall_progress_percent: int = 0
    skill_scores: dict[str, int | None] = Field(default_factory=dict)
    levels: dict[str, str | None] = Field(default_factory=dict)
    strongest_skill: str | None = None
    strongest_skill_ar: str | None = None
    weakest_skill: str | None = None
    weakest_skill_ar: str | None = None
    improvement_trend: LanguageImprovementTrendOut = Field(default_factory=LanguageImprovementTrendOut)
    statistics: LanguageStatisticsOut = Field(default_factory=LanguageStatisticsOut)
    achievements: LanguageAchievementsOut = Field(default_factory=LanguageAchievementsOut)
    recent_badges: list[LanguageAchievementItemOut] = Field(default_factory=list)
    scenario_progress: list[LanguageScenarioProgressOut] = Field(default_factory=list)
    skill_radar: list[LanguageSkillRadarOut] = Field(default_factory=list)
    daily_mission: LanguageDailyMissionOut = Field(default_factory=LanguageDailyMissionOut)
    streak: dict = Field(default_factory=dict)
    skill_growth: dict = Field(default_factory=dict)


class ParentLanguageAnalyticsSummaryOut(BaseModel):
    current_cefr_level: str | None = None
    strongest_skill: str | None = None
    strongest_skill_ar: str | None = None
    weakest_skill: str | None = None
    weakest_skill_ar: str | None = None
    completed_scenarios: int = 0
    achievements_count: int = 0
    overall_progress_percent: int = 0
    adaptive_recommendation: str | None = None
