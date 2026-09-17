"""Types for the Adaptive Challenge Engine (Phase 3.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.services.language_listening_confidence.types import ConfidenceAwareRecommendation, ConfidenceState


class ChallengeLevel(StrEnum):
    easy = "easy"
    normal = "normal"
    hard = "hard"
    exam = "exam"


@dataclass
class ChallengeLessonRecord:
    lesson_index: int
    accuracy: float
    passed: bool
    confidence_trend: float
    evidence_growth: float
    review_performance: float
    was_review: bool
    success_streak: int
    failure_streak: int
    time_spent_sec: float | None = None
    hint_count: int = 0
    retry_count: int = 0
    lesson_score: float = 0.5

    def to_dict(self) -> dict[str, object]:
        return {
            "lesson_index": self.lesson_index,
            "accuracy": round(self.accuracy, 4),
            "passed": self.passed,
            "confidence_trend": round(self.confidence_trend, 4),
            "evidence_growth": round(self.evidence_growth, 4),
            "review_performance": round(self.review_performance, 4),
            "was_review": self.was_review,
            "success_streak": self.success_streak,
            "failure_streak": self.failure_streak,
            "time_spent_sec": self.time_spent_sec,
            "hint_count": self.hint_count,
            "retry_count": self.retry_count,
            "lesson_score": round(self.lesson_score, 4),
        }


@dataclass
class ChallengeState:
    level: str
    current_level: ChallengeLevel = ChallengeLevel.normal
    challenge_score: float = 0.5
    promotion_count: int = 0
    demotion_count: int = 0
    promote_streak: int = 0
    demote_streak: int = 0
    lesson_index: int = 0
    history: list[ChallengeLessonRecord] = field(default_factory=list)
    adjustment_history: list[dict[str, object]] = field(default_factory=list)
    last_adjustment_reason: str = "initial"

    def to_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "current_level": self.current_level.value,
            "challenge_score": round(self.challenge_score, 4),
            "promotion_count": self.promotion_count,
            "demotion_count": self.demotion_count,
            "promote_streak": self.promote_streak,
            "demote_streak": self.demote_streak,
            "lesson_index": self.lesson_index,
            "history": [rec.to_dict() for rec in self.history[-15:]],
            "adjustment_history": self.adjustment_history[-32:],
            "last_adjustment_reason": self.last_adjustment_reason,
        }


@dataclass(frozen=True, slots=True)
class ChallengeAwareRecommendation:
    confidence_aware: ConfidenceAwareRecommendation
    challenge_state: ChallengeState
    challenge_boost: float
    blended_score: float
    challenge_influence_pct: float
    effective_difficulty_band: str
    challenge_level: ChallengeLevel
    selection_reason: str

    @property
    def recommendation(self):
        return self.confidence_aware.recommendation

    @property
    def goal_aware(self):
        return self.confidence_aware.goal_aware

    @property
    def confidence_state(self) -> ConfidenceState:
        return self.confidence_aware.confidence_state

    @property
    def plan(self):
        return self.confidence_aware.plan

    @property
    def skill_focus(self):
        return self.confidence_aware.skill_focus

    @property
    def objectives(self):
        return self.confidence_aware.objectives

    @property
    def knowledge_node(self):
        return self.confidence_aware.knowledge_node

    @property
    def review_objectives(self):
        return self.confidence_aware.review_objectives

    @property
    def score(self):
        return self.confidence_aware.score

    @property
    def curriculum_stage(self):
        return self.confidence_aware.curriculum_stage

    @property
    def lesson_intent(self):
        return self.confidence_aware.lesson_intent

    def to_metadata(self) -> dict[str, object]:
        base = self.confidence_aware.to_metadata()
        base.update(
            {
                "challenge_level": self.challenge_level.value,
                "challenge_label": f"{self.challenge_state.level} {self.challenge_level.value.title()}",
                "challenge_score": round(self.challenge_state.challenge_score, 4),
                "challenge_boost": round(self.challenge_boost, 4),
                "challenge_blended_score": round(self.blended_score, 4),
                "challenge_influence_pct": round(self.challenge_influence_pct, 4),
                "effective_difficulty_band": self.effective_difficulty_band,
                "challenge_selection_reason": self.selection_reason,
                "promotion_count": self.challenge_state.promotion_count,
                "demotion_count": self.challenge_state.demotion_count,
                "promote_streak": self.challenge_state.promote_streak,
                "demote_streak": self.challenge_state.demote_streak,
            }
        )
        return base


@dataclass(frozen=True, slots=True)
class ChallengeTelemetry:
    level: str
    current_challenge: str
    challenge_score: float
    promotion_count: int
    demotion_count: int
    promote_streak: int
    demote_streak: int
    lesson_index: int
    average_lesson_score: float
    challenge_history: list[str]
    adjustment_history: list[dict[str, object]]
    last_adjustment_reason: str
