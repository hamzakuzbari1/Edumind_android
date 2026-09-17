"""Types for Writing Journey (W0)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing_explainability.types import TrendFacts


@dataclass(frozen=True, slots=True)
class WritingJourneyGoal:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class WritingJourneyMission:
    """Today's mission pointer."""

    lesson_id: int | None
    title: str
    status: str
    teaser: str = ""


@dataclass(frozen=True, slots=True)
class WritingJourneyPromotion:
    """Promotion journey in educational language — no engine terms."""

    headline: str
    checklist: tuple[str, ...]
    eligible_for_level_test: bool
    level_test_label: str = "Writing level test"


@dataclass(frozen=True, slots=True)
class WritingJourneyBundle:
    """Canonical journey-scoped bundle."""

    official_writing_level: str
    learning_stage_label: str
    personal_goal: WritingJourneyGoal
    todays_mission: WritingJourneyMission
    weak_skills: tuple[str, ...]
    progress_summary: str
    next_milestone: str
    promotion: WritingJourneyPromotion
    trend: TrendFacts | None = None
    portfolio_teaser: str = ""
    builder_version: str = "0.1.0"

    def to_student_dict(self) -> dict[str, object]:
        return {
            "official_writing_level": self.official_writing_level,
            "learning_stage_label": self.learning_stage_label,
            "personal_goal": {"id": self.personal_goal.id, "label": self.personal_goal.label},
            "todays_mission": {
                "lesson_id": self.todays_mission.lesson_id,
                "title": self.todays_mission.title,
                "status": self.todays_mission.status,
                "teaser": self.todays_mission.teaser,
            },
            "weak_skills": list(self.weak_skills),
            "progress_summary": self.progress_summary,
            "next_milestone": self.next_milestone,
            "promotion": {
                "headline": self.promotion.headline,
                "checklist": list(self.promotion.checklist),
                "eligible_for_level_test": self.promotion.eligible_for_level_test,
                "level_test_label": self.promotion.level_test_label,
            },
            "trend": self.trend.to_dict() if self.trend else None,
            "portfolio_teaser": self.portfolio_teaser,
        }
