"""Listening Confidence + Evidence Engine (Phase 3.2 / 3.2.1)."""

from app.services.language_listening_confidence.adapter import (
    confidence_to_objective_progress,
    mastered_objectives,
    under_confident_objectives,
)
from app.services.language_listening_confidence.constants import (
    CONFIDENCE_INFLUENCE,
    CONFIDENCE_KEY,
    EVIDENCE_INFLUENCE,
    LESSON_CONFIDENCE_KEY,
    MASTERY_SCORE_THRESHOLD,
    MASTERY_THRESHOLD,
    MAX_SINGLE_STEP,
)
from app.services.language_listening_confidence.engine import recommend_confidence_aware_listening_plan
from app.services.language_listening_confidence.evidence import (
    compute_coverage_score,
    compute_mastery_score,
    missing_evidence,
    objectives_needing_evidence,
    plan_evidence_fill_score,
    record_evidence_from_lesson,
)
from app.services.language_listening_confidence.storage import (
    build_initial_confidence_state,
    load_confidence_state,
    load_student_confidence,
    save_student_confidence,
    serialize_confidence_state,
)
from app.services.language_listening_confidence.telemetry import compute_confidence_telemetry
from app.services.language_listening_confidence.types import (
    ConfidenceAwareRecommendation,
    ConfidenceState,
    ConfidenceTelemetry,
    LessonConfidenceContext,
    ObjectiveConfidenceRecord,
    ObjectiveEvidenceRecord,
)
from app.services.language_listening_confidence.update import (
    apply_decay,
    apply_decay_to_state,
    update_confidence_from_lesson,
)

__all__ = (
    "CONFIDENCE_INFLUENCE",
    "CONFIDENCE_KEY",
    "EVIDENCE_INFLUENCE",
    "LESSON_CONFIDENCE_KEY",
    "MASTERY_SCORE_THRESHOLD",
    "MASTERY_THRESHOLD",
    "MAX_SINGLE_STEP",
    "ConfidenceAwareRecommendation",
    "ConfidenceState",
    "ConfidenceTelemetry",
    "LessonConfidenceContext",
    "ObjectiveConfidenceRecord",
    "ObjectiveEvidenceRecord",
    "apply_decay",
    "apply_decay_to_state",
    "build_initial_confidence_state",
    "compute_confidence_telemetry",
    "compute_coverage_score",
    "compute_mastery_score",
    "confidence_to_objective_progress",
    "load_confidence_state",
    "load_student_confidence",
    "mastered_objectives",
    "missing_evidence",
    "objectives_needing_evidence",
    "plan_evidence_fill_score",
    "recommend_confidence_aware_listening_plan",
    "record_evidence_from_lesson",
    "save_student_confidence",
    "serialize_confidence_state",
    "under_confident_objectives",
    "update_confidence_from_lesson",
)
