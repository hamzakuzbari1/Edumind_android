"""Student Speaking Knowledge Model types (S2).

Field consumer map:
- mastery, confidence, stability → S8 diagnostic, S9 planner
- evidence_dimension_coverage → S7 gate, S8 incomplete-skill detection
- mistake_patterns → S8 remediation routing, S12 coach hints
- retention_risk → S8 spaced review, S15 stage signals
- current_status → S8 journey summaries (derived, also cached)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

KNOWLEDGE_MODEL_SCHEMA_VERSION = "2.0.0"
OBSERVATION_HISTORY_CAP = 12
OBSERVATION_INDEX_CAP = 256
MISTAKE_TAG_HISTORY_CAP = 8


class SpeakingSkillStatus(StrEnum):
    """Deterministic educational status — no optimistic defaults."""

    unseen = "unseen"
    observed = "observed"
    developing = "developing"
    stable = "stable"
    mastered = "mastered"
    at_risk = "at_risk"


class ObservationSourceType(StrEnum):
    """Canonical observation origin (no provider names)."""

    evaluation_turn = "evaluation_turn"
    lesson_attempt = "lesson_attempt"
    promotion_assessment = "promotion_assessment"
    synthetic_test = "synthetic_test"


@dataclass(frozen=True, slots=True)
class SpeakingSkillEvidenceObservation:
    """Canonical bridge from S7 evaluation facts into S2 (S2 verifies with synthetic data)."""

    observation_id: str
    skill_id: str
    observed_at: str  # ISO-8601 UTC
    performance: float
    confidence: float
    evidence_dimensions: tuple[str, ...]
    context_id: str
    success: bool
    target_skill: bool = True
    session_id: str = ""
    lesson_id: str = ""
    mistake_tags: tuple[str, ...] = ()
    revision_number: int = 0
    previous_observation_id: str | None = None
    communicative_impact: float | None = None
    source_type: ObservationSourceType = ObservationSourceType.evaluation_turn


@dataclass
class SkillObservationRecord:
    """Bounded per-skill history entry."""

    observation_id: str
    observed_at: str
    performance: float
    confidence: float
    context_id: str
    success: bool
    revision_number: int = 0
    mistake_tags: list[str] = field(default_factory=list)


@dataclass
class StudentSpeakingSkillState:
    """Per-skill educational state for one student."""

    skill_id: str
    mastery: float = 0.0
    confidence: float = 0.0
    evidence_count: int = 0
    successful_evidence_count: int = 0
    recent_performance: float = 0.0
    stability: float = 0.0
    mistake_recurrence: float = 0.0
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    last_practiced_at: str | None = None
    first_observed_at: str | None = None
    last_updated_at: str | None = None
    retention_risk: float = 0.0
    revision_improvement: float = 0.0
    distinct_context_count: int = 0
    observed_dimensions: dict[str, int] = field(default_factory=dict)
    context_fingerprints: list[str] = field(default_factory=list)
    mistake_tag_counts: dict[str, int] = field(default_factory=dict)
    recent_mistake_tags: list[str] = field(default_factory=list)
    observation_history: list[SkillObservationRecord] = field(default_factory=list)
    current_status: SpeakingSkillStatus = SpeakingSkillStatus.unseen
    meets_mastery_requirements: bool = False
    peak_mastery: float = 0.0
    peak_stability: float = 0.0


@dataclass
class MistakePatternSummary:
    """Aggregated mistake recurrence for diagnostic consumers."""

    mistake_tag: str
    occurrence_count: int
    recent_occurrence_count: int
    last_seen_at: str | None
    affected_contexts: list[str] = field(default_factory=list)


@dataclass
class StudentSpeakingKnowledgeModel:
    """Student-level speaking knowledge snapshot."""

    student_id: int
    language_id: int
    schema_version: str = KNOWLEDGE_MODEL_SCHEMA_VERSION
    graph_version: str = ""
    skill_states: dict[str, StudentSpeakingSkillState] = field(default_factory=dict)
    deprecated_skill_states: dict[str, StudentSpeakingSkillState] = field(default_factory=dict)
    mistake_patterns: dict[str, MistakePatternSummary] = field(default_factory=dict)
    applied_observation_ids: dict[str, str] = field(default_factory=dict)
    total_observations: int = 0
    last_updated_at: str | None = None
    compatibility_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EvidenceCoverage:
    """Required vs observed evidence dimensions for a skill."""

    required_dimensions: tuple[str, ...]
    observed_dimensions: tuple[str, ...]
    missing_dimensions: tuple[str, ...]
    coverage_ratio: float


@dataclass(frozen=True, slots=True)
class ObservationApplyResult:
    """Result of applying one observation."""

    applied: bool
    idempotent: bool = False
    skill_id: str = ""
    reason: str = ""
    state: StudentSpeakingSkillState | None = None


@dataclass(frozen=True, slots=True)
class MasteryRequirementEvaluation:
    """S1 requirement gate evaluation."""

    met: bool
    reasons: tuple[str, ...]


def skill_state_to_dict(state: StudentSpeakingSkillState) -> dict[str, Any]:
    return {
        "skill_id": state.skill_id,
        "mastery": state.mastery,
        "confidence": state.confidence,
        "evidence_count": state.evidence_count,
        "successful_evidence_count": state.successful_evidence_count,
        "recent_performance": state.recent_performance,
        "stability": state.stability,
        "mistake_recurrence": state.mistake_recurrence,
        "consecutive_successes": state.consecutive_successes,
        "consecutive_failures": state.consecutive_failures,
        "last_practiced_at": state.last_practiced_at,
        "first_observed_at": state.first_observed_at,
        "last_updated_at": state.last_updated_at,
        "retention_risk": state.retention_risk,
        "revision_improvement": state.revision_improvement,
        "distinct_context_count": state.distinct_context_count,
        "observed_dimensions": dict(state.observed_dimensions),
        "context_fingerprints": list(state.context_fingerprints),
        "mistake_tag_counts": dict(state.mistake_tag_counts),
        "recent_mistake_tags": list(state.recent_mistake_tags),
        "observation_history": [
            {
                "observation_id": r.observation_id,
                "observed_at": r.observed_at,
                "performance": r.performance,
                "confidence": r.confidence,
                "context_id": r.context_id,
                "success": r.success,
                "revision_number": r.revision_number,
                "mistake_tags": list(r.mistake_tags),
            }
            for r in state.observation_history
        ],
        "current_status": state.current_status.value,
        "meets_mastery_requirements": state.meets_mastery_requirements,
        "peak_mastery": state.peak_mastery,
        "peak_stability": state.peak_stability,
    }


def skill_state_from_dict(raw: dict[str, Any]) -> StudentSpeakingSkillState:
    history_raw = raw.get("observation_history") or []
    history: list[SkillObservationRecord] = []
    if isinstance(history_raw, list):
        for item in history_raw:
            if not isinstance(item, dict):
                continue
            history.append(
                SkillObservationRecord(
                    observation_id=str(item.get("observation_id", "")),
                    observed_at=str(item.get("observed_at", "")),
                    performance=float(item.get("performance", 0.0)),
                    confidence=float(item.get("confidence", 0.0)),
                    context_id=str(item.get("context_id", "")),
                    success=bool(item.get("success", False)),
                    revision_number=int(item.get("revision_number", 0)),
                    mistake_tags=[str(t) for t in (item.get("mistake_tags") or [])],
                )
            )
    status_raw = str(raw.get("current_status", SpeakingSkillStatus.unseen.value))
    try:
        status = SpeakingSkillStatus(status_raw)
    except ValueError:
        status = SpeakingSkillStatus.unseen
    return StudentSpeakingSkillState(
        skill_id=str(raw.get("skill_id", "")),
        mastery=float(raw.get("mastery", 0.0)),
        confidence=float(raw.get("confidence", 0.0)),
        evidence_count=int(raw.get("evidence_count", 0)),
        successful_evidence_count=int(raw.get("successful_evidence_count", 0)),
        recent_performance=float(raw.get("recent_performance", 0.0)),
        stability=float(raw.get("stability", 0.0)),
        mistake_recurrence=float(raw.get("mistake_recurrence", 0.0)),
        consecutive_successes=int(raw.get("consecutive_successes", 0)),
        consecutive_failures=int(raw.get("consecutive_failures", 0)),
        last_practiced_at=raw.get("last_practiced_at"),
        first_observed_at=raw.get("first_observed_at"),
        last_updated_at=raw.get("last_updated_at"),
        retention_risk=float(raw.get("retention_risk", 0.0)),
        revision_improvement=float(raw.get("revision_improvement", 0.0)),
        distinct_context_count=int(raw.get("distinct_context_count", 0)),
        observed_dimensions={str(k): int(v) for k, v in (raw.get("observed_dimensions") or {}).items()},
        context_fingerprints=[str(c) for c in (raw.get("context_fingerprints") or [])],
        mistake_tag_counts={str(k): int(v) for k, v in (raw.get("mistake_tag_counts") or {}).items()},
        recent_mistake_tags=[str(t) for t in (raw.get("recent_mistake_tags") or [])],
        observation_history=history,
        current_status=status,
        meets_mastery_requirements=bool(raw.get("meets_mastery_requirements", False)),
        peak_mastery=float(raw.get("peak_mastery", 0.0)),
        peak_stability=float(raw.get("peak_stability", 0.0)),
    )
