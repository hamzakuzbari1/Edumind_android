"""Types for the Goal-Aware Learning Engine (Phase 3.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.services.language_listening_curriculum.types import CurriculumRecommendation


class LearningGoal(StrEnum):
    academic = "academic"
    ielts = "ielts"
    toefl = "toefl"
    business = "business"
    job_interview = "job_interview"
    travel = "travel"
    daily_life = "daily_life"
    university = "university"
    conversation = "conversation"
    general_english = "general_english"


@dataclass(frozen=True, slots=True)
class LearningGoalProfile:
    goal: LearningGoal
    label: str
    preferred_situations: frozenset[str]
    preferred_narrative_formats: frozenset[str]
    preferred_format_hints: frozenset[str]
    preferred_objectives: tuple[str, ...]
    vocabulary_domains: tuple[str, ...]
    preferred_pace: frozenset[str]
    preferred_narrative_styles: frozenset[str]
    preferred_categories: frozenset[str]
    difficulty_progression: str
    knowledge_chain_preference: str
    style_directives: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GoalAlignmentScore:
    total: float
    situation_fit: float
    format_fit: float
    objective_fit: float
    vocabulary_fit: float
    pace_fit: float
    narrative_fit: float
    category_fit: float
    difficulty_fit: float
    knowledge_fit: float
    contributions: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GoalAwareRecommendation:
    recommendation: CurriculumRecommendation
    learning_goal: LearningGoal
    goal_profile_label: str
    goal_alignment: GoalAlignmentScore
    blended_score: float
    goal_influence_pct: float
    goal_objective_hints: tuple[str, ...]
    selection_reason: str

    @property
    def plan(self):
        return self.recommendation.plan

    @property
    def skill_focus(self):
        return self.recommendation.skill_focus

    @property
    def objectives(self):
        return self.recommendation.objectives

    @property
    def knowledge_node(self):
        return self.recommendation.knowledge_node

    @property
    def review_objectives(self):
        return self.recommendation.review_objectives

    @property
    def score(self):
        return self.recommendation.score

    @property
    def curriculum_stage(self):
        return self.recommendation.curriculum_stage

    @property
    def lesson_intent(self):
        return self.recommendation.lesson_intent

    def to_metadata(self) -> dict[str, object]:
        base = self.recommendation.to_metadata()
        base.update(
            {
                "learning_goal": self.learning_goal.value,
                "goal_profile": self.goal_profile_label,
                "goal_alignment_score": round(self.goal_alignment.total, 4),
                "blended_score": round(self.blended_score, 4),
                "goal_influence_pct": round(self.goal_influence_pct, 4),
                "goal_objective_hints": list(self.goal_objective_hints),
                "goal_score_breakdown": {
                    "situation_fit": round(self.goal_alignment.situation_fit, 4),
                    "format_fit": round(self.goal_alignment.format_fit, 4),
                    "objective_fit": round(self.goal_alignment.objective_fit, 4),
                    "vocabulary_fit": round(self.goal_alignment.vocabulary_fit, 4),
                    "pace_fit": round(self.goal_alignment.pace_fit, 4),
                    "narrative_fit": round(self.goal_alignment.narrative_fit, 4),
                    "category_fit": round(self.goal_alignment.category_fit, 4),
                    "difficulty_fit": round(self.goal_alignment.difficulty_fit, 4),
                    "knowledge_fit": round(self.goal_alignment.knowledge_fit, 4),
                },
                "goal_contributions": self.goal_alignment.contributions,
                "goal_selection_reason": self.selection_reason,
            }
        )
        return base
