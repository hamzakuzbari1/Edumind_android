"""Types for Promotion Readiness Stability (Phase 5.3.1)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PromotionPrediction(StrEnum):
    VERY_LIKELY = "Very Likely"
    LIKELY = "Likely"
    BORDERLINE = "Borderline"
    UNCERTAIN = "Uncertain"
    NOT_READY = "Not Ready"


@dataclass(frozen=True, slots=True)
class ReadinessHistoryEntry:
    lesson_index: int
    readiness_score: int
    gate_eligible: bool
    confidence_avg: float
    evidence_coverage_avg: float
    review_completion_ratio: float
    recent_consistency: float
    challenge_score: float

    def to_dict(self) -> dict[str, object]:
        return {
            "lesson_index": self.lesson_index,
            "readiness_score": self.readiness_score,
            "gate_eligible": self.gate_eligible,
            "confidence_avg": round(self.confidence_avg, 4),
            "evidence_coverage_avg": round(self.evidence_coverage_avg, 4),
            "review_completion_ratio": round(self.review_completion_ratio, 4),
            "recent_consistency": round(self.recent_consistency, 4),
            "challenge_score": round(self.challenge_score, 4),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReadinessHistoryEntry:
        return cls(
            lesson_index=int(data.get("lesson_index", 0)),
            readiness_score=int(data.get("readiness_score", 0)),
            gate_eligible=bool(data.get("gate_eligible", False)),
            confidence_avg=float(data.get("confidence_avg", 0.0)),
            evidence_coverage_avg=float(data.get("evidence_coverage_avg", 0.0)),
            review_completion_ratio=float(data.get("review_completion_ratio", 0.0)),
            recent_consistency=float(data.get("recent_consistency", 0.0)),
            challenge_score=float(data.get("challenge_score", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class RollingReadinessStats:
    last_readiness_scores: tuple[int, ...]
    rolling_average: float
    rolling_minimum: float
    rolling_variance: float
    stable_lessons: int
    best_streak: int
    current_streak: int


@dataclass(frozen=True, slots=True)
class PromotionStabilityTelemetry:
    official_cefr: str
    current_readiness_score: int
    smoothed_readiness: float
    history_length: int
    gate_pass_recent: tuple[bool, ...]
    confidence_trend: float
    evidence_trend: float
    review_trend: float
    consistency_trend: float
    skill: str = "listening"


@dataclass(frozen=True, slots=True)
class PromotionStabilityResult:
    official_cefr: str
    promotion_confidence: int
    readiness_stability: float
    rolling_average: float
    rolling_minimum: float
    rolling_variance: float
    current_streak: int
    best_streak: int
    stable_lessons: int
    last_readiness_scores: tuple[int, ...]
    prediction: PromotionPrediction
    recommendation: str
    recommendations: tuple[str, ...]
    telemetry: PromotionStabilityTelemetry
