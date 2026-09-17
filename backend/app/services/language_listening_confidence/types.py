"""Types for the Listening Confidence Engine (Phase 3.2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_learning_goal.types import GoalAwareRecommendation
from app.services.language_listening_curriculum.types import CurriculumRecommendation


@dataclass
class ObjectiveEvidenceRecord:
    difficulty: dict[str, int] = field(default_factory=dict)
    formats: dict[str, int] = field(default_factory=dict)
    topics: dict[str, int] = field(default_factory=dict)
    speakers: dict[str, int] = field(default_factory=dict)
    speed: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "difficulty": dict(self.difficulty),
            "formats": dict(self.formats),
            "topics": dict(self.topics),
            "speakers": dict(self.speakers),
            "speed": dict(self.speed),
        }


@dataclass
class ObjectiveConfidenceRecord:
    objective_id: str
    label: str
    confidence: float = 0.35
    last_update_index: int = -1
    trend: float = 0.0
    total_gain: float = 0.0
    total_decay: float = 0.0
    success_streak: int = 0
    mistake_streak: int = 0
    exposure_count: int = 0
    history: list[float] = field(default_factory=list)
    evidence: ObjectiveEvidenceRecord = field(default_factory=ObjectiveEvidenceRecord)

    @property
    def coverage_score(self) -> float:
        from app.services.language_listening_confidence.evidence import compute_coverage_score

        return compute_coverage_score(self.evidence)

    @property
    def mastery_score(self) -> float:
        from app.services.language_listening_confidence.evidence import compute_mastery_score

        return compute_mastery_score(self.confidence, self.coverage_score)

    @property
    def is_mastered(self) -> bool:
        from app.services.language_listening_confidence.evidence import is_evidence_mastered

        return is_evidence_mastered(self.confidence, self.coverage_score)

    def to_dict(self) -> dict[str, object]:
        from app.services.language_listening_confidence.evidence import missing_evidence

        return {
            "objective_id": self.objective_id,
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "coverage_score": self.coverage_score,
            "mastery_score": self.mastery_score,
            "last_update_index": self.last_update_index,
            "trend": round(self.trend, 4),
            "total_gain": round(self.total_gain, 4),
            "total_decay": round(self.total_decay, 4),
            "success_streak": self.success_streak,
            "mistake_streak": self.mistake_streak,
            "exposure_count": self.exposure_count,
            "history": [round(v, 4) for v in self.history[-24:]],
            "evidence": self.evidence.to_dict(),
            "missing_evidence": missing_evidence(self),
            "mastered": self.is_mastered,
        }


@dataclass
class ConfidenceState:
    level: str
    objectives: dict[str, ObjectiveConfidenceRecord] = field(default_factory=dict)
    lesson_index: int = 0
    last_decay_index: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "lesson_index": self.lesson_index,
            "objectives": {oid: rec.to_dict() for oid, rec in self.objectives.items()},
        }


@dataclass(frozen=True, slots=True)
class LessonConfidenceContext:
    situation: str
    narrative_format: str
    format_hint: str
    difficulty_band: str
    speaker_count: int
    lesson_objectives: tuple[str, ...]
    skill_focus: tuple[str, ...]
    lesson_index: int
    category: str = ""
    pace: str = "conversational"


@dataclass(frozen=True, slots=True)
class ConfidenceAwareRecommendation:
    recommendation: CurriculumRecommendation
    goal_aware: GoalAwareRecommendation | None
    confidence_state: ConfidenceState
    confidence_boost: float
    blended_score: float
    confidence_influence_pct: float
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
                "confidence_boost": round(self.confidence_boost, 4),
                "confidence_blended_score": round(self.blended_score, 4),
                "confidence_influence_pct": round(self.confidence_influence_pct, 4),
                "confidence_selection_reason": self.selection_reason,
                "objective_confidence_snapshot": {
                    oid: {
                        "confidence": round(rec.confidence, 4),
                        "coverage": rec.coverage_score,
                        "mastery": rec.mastery_score,
                    }
                    for oid, rec in self.confidence_state.objectives.items()
                    if oid in self.objectives or oid in self.review_objectives
                },
            }
        )
        if self.goal_aware is not None:
            base["learning_goal"] = self.goal_aware.learning_goal.value
        return base


@dataclass
class ConfidenceTelemetry:
    level: str = ""
    lesson_index: int = 0
    mastered_count: int = 0
    confidence_only_mastered: int = 0
    under_confident: list[str] = field(default_factory=list)
    high_confidence: list[str] = field(default_factory=list)
    needs_evidence: list[str] = field(default_factory=list)
    average_confidence: float = 0.0
    average_coverage: float = 0.0
    average_mastery_score: float = 0.0
    total_gain: float = 0.0
    total_decay: float = 0.0
    confidence_by_objective: dict[str, float] = field(default_factory=dict)
    coverage_by_objective: dict[str, float] = field(default_factory=dict)
    mastery_by_objective: dict[str, float] = field(default_factory=dict)
    trends: dict[str, float] = field(default_factory=dict)
    review_due: list[str] = field(default_factory=list)
    missing_evidence_summary: dict[str, dict[str, list[str]]] = field(default_factory=dict)
