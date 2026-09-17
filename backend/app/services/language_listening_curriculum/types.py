"""Types for the Learning Curriculum Engine (Phase 2.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.services.language_listening_intelligence.types import ListeningIntelligencePlan


class ObjectiveState(StrEnum):
    introduced = "introduced"
    practicing = "practicing"
    mastered = "mastered"


class ListeningSkillFocus(StrEnum):
    main_idea = "main_idea"
    detail = "detail"
    inference = "inference"
    purpose = "purpose"
    speaker_intention = "speaker_intention"
    tone = "tone"
    prediction = "prediction"
    sequence = "sequence"
    opinion = "opinion"
    bias = "bias"


@dataclass(frozen=True, slots=True)
class CurriculumHistoryEntry:
    situation: str
    category: str
    narrative_format: str
    skill_focus: tuple[str, ...]
    objectives: tuple[str, ...]
    knowledge_node: str
    level: str
    generation_index: int = 0
    lesson_intent: str = "balanced_coverage"


@dataclass(frozen=True, slots=True)
class ObjectiveProgress:
    objective_id: str
    label: str
    state: ObjectiveState
    exposure_count: int = 0
    last_seen_index: int = -1


@dataclass(frozen=True, slots=True)
class CurriculumRecommendationScore:
    total: float
    cefr_suitability: float
    curriculum_progression: float
    weak_skill_recovery: float
    review_priority: float
    topic_diversity: float
    category_diversity: float
    interest_weight: float
    difficulty_rotation: float
    narrative_rotation: float
    cooldown: float
    intelligence_base: float
    fatigue_relief: float
    coverage_balance: float = 0.0
    knowledge_dependency: float = 0.0
    intent_fit: float = 0.0
    contributions: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CurriculumRecommendation:
    plan: ListeningIntelligencePlan
    skill_focus: tuple[str, ...]
    objectives: tuple[str, ...]
    knowledge_node: str
    review_objectives: tuple[str, ...]
    score: CurriculumRecommendationScore
    curriculum_stage: str
    selection_reason: str
    lesson_intent: str = "balanced_coverage"

    def to_metadata(self) -> dict[str, object]:
        return {
            "skill_focus": list(self.skill_focus),
            "objectives": list(self.objectives),
            "knowledge_node": self.knowledge_node,
            "review_objectives": list(self.review_objectives),
            "curriculum_stage": self.curriculum_stage,
            "lesson_intent": self.lesson_intent,
            "recommendation_score": round(self.score.total, 4),
            "score_breakdown": {
                "cefr_suitability": round(self.score.cefr_suitability, 4),
                "curriculum_progression": round(self.score.curriculum_progression, 4),
                "weak_skill_recovery": round(self.score.weak_skill_recovery, 4),
                "review_priority": round(self.score.review_priority, 4),
                "coverage_balance": round(self.score.coverage_balance, 4),
                "knowledge_dependency": round(self.score.knowledge_dependency, 4),
                "intent_fit": round(self.score.intent_fit, 4),
                "topic_diversity": round(self.score.topic_diversity, 4),
                "category_diversity": round(self.score.category_diversity, 4),
                "interest_weight": round(self.score.interest_weight, 4),
                "difficulty_rotation": round(self.score.difficulty_rotation, 4),
                "narrative_rotation": round(self.score.narrative_rotation, 4),
                "cooldown": round(self.score.cooldown, 4),
                "intelligence_base": round(self.score.intelligence_base, 4),
                "fatigue_relief": round(self.score.fatigue_relief, 4),
            },
            "score_contributions": self.score.contributions,
            "selection_reason": self.selection_reason,
        }


@dataclass
class CurriculumTelemetry:
    current_stage: str = "exploring"
    skill_coverage: dict[str, int] = field(default_factory=dict)
    skill_coverage_pct: dict[str, float] = field(default_factory=dict)
    objectives_mastered: list[str] = field(default_factory=list)
    objectives_under_practiced: list[str] = field(default_factory=list)
    objective_coverage_pct: dict[str, float] = field(default_factory=dict)
    review_queue: list[str] = field(default_factory=list)
    knowledge_node: str = ""
    average_recommendation_score: float = 0.0
    weak_skills_targeted: list[str] = field(default_factory=list)
    neglected_skills: list[str] = field(default_factory=list)
    intent_distribution: dict[str, float] = field(default_factory=dict)
    weak_skill_pct: float = 0.0
    review_pct: float = 0.0
    score_contributions_avg: dict[str, float] = field(default_factory=dict)
