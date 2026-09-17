"""Types for the Listening Promotion Readiness Engine (Phase 5.3)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReadinessStatus(StrEnum):
    NOT_READY = "NOT_READY"
    ALMOST_READY = "ALMOST_READY"
    READY = "READY"
    PROMOTION_AVAILABLE = "PROMOTION_AVAILABLE"


@dataclass(frozen=True, slots=True)
class ReadinessDimensionScore:
    name: str
    current: float
    required: float
    progress: float  # 0..1+
    weight: float
    contribution: float  # progress * weight * 100


@dataclass(frozen=True, slots=True)
class PromotionReadinessTelemetry:
    official_cefr: str
    persistent_stage: int
    stage_score: int
    gate_overall_score: float
    gate_eligible: bool
    dimension_scores: tuple[ReadinessDimensionScore, ...]
    skill: str = "listening"


@dataclass(frozen=True, slots=True)
class PromotionReadinessResult:
    official_cefr: str
    readiness_score: int
    status: ReadinessStatus
    estimated_remaining: float
    primary_blockers: tuple[str, ...]
    secondary_blockers: tuple[str, ...]
    strengths: tuple[str, ...]
    next_actions: tuple[str, ...]
    telemetry: PromotionReadinessTelemetry
