"""Types for the Listening Promotion Test Engine (Phase 5.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PromotionTestOutcome(StrEnum):
    PASS = "PASS"
    BORDERLINE = "BORDERLINE"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class PromotionTestEligibility:
    eligible: bool
    reason: str
    official_cefr: str
    target_cefr: str
    readiness_score: int
    readiness_status: str


@dataclass(frozen=True, slots=True)
class PromotionAssessmentSpec:
    assessment_id: str
    lesson_id: str
    objective_id: str
    objective_label: str
    situation: str
    format: str
    speaker_count: int
    difficulty_band: str
    question: str
    choices: tuple[str, ...]
    correct_index: int
    sequence_index: int

    def to_public_dict(self) -> dict[str, object]:
        return {
            "assessment_id": self.assessment_id,
            "lesson_id": self.lesson_id,
            "objective_id": self.objective_id,
            "objective_label": self.objective_label,
            "situation": self.situation,
            "format": self.format,
            "speaker_count": self.speaker_count,
            "difficulty_band": self.difficulty_band,
            "question": self.question,
            "choices": list(self.choices),
            "sequence_index": self.sequence_index,
        }


@dataclass
class PromotionTestSession:
    session_id: str
    student_id: int
    language_id: int
    official_cefr: str
    target_cefr: str
    attempt_number: int
    assessments: list[PromotionAssessmentSpec]
    expires_at: float
    objective_sequence: tuple[str, ...] = ()
    lesson_ids: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "official_cefr": self.official_cefr,
            "target_cefr": self.target_cefr,
            "attempt_number": self.attempt_number,
            "assessment_count": len(self.assessments),
            "assessments": [a.to_public_dict() for a in self.assessments],
        }


@dataclass(frozen=True, slots=True)
class PromotionTestScoreBreakdown:
    overall_score: float
    objective_scores: dict[str, float]
    evidence_score: float
    consistency_score: float
    coverage_score: float
    exam_confidence: float


@dataclass(frozen=True, slots=True)
class PromotionTestTelemetry:
    session_id: str
    attempt_number: int
    official_cefr: str
    target_cefr: str
    assessments_correct: int
    assessments_total: int
    objective_coverage: tuple[str, ...]
    lesson_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PromotionTestResult:
    session_id: str
    overall_score: float
    result: PromotionTestOutcome
    objective_scores: dict[str, float]
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    recommendation: str
    telemetry: PromotionTestTelemetry
    score_breakdown: PromotionTestScoreBreakdown
