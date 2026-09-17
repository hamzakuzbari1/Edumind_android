"""Speaking learning stage signal types (S15).

INTERNAL ONLY — not student UI numbers. S15 aggregates deterministic evidence
signals for S16 transition_gate consumption. Never advances stage, CEFR, or
promotion readiness, and never mutates S2.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.services.language_speaking.enums import SpeakingLearningStage

LANGUAGE_SPEAKING_LEARNING_STAGE_VERSION = "15.0.0"
STAGE_SIGNAL_SCHEMA_VERSION = "15.0.0"

# Keep stub type for any legacy import paths; S15 replaces the real engine surface.
@dataclass(frozen=True, slots=True)
class SpeakingLearningStageResult:
    """Legacy S0 placeholder — prefer SpeakingStageSignalSnapshot for S15+."""

    stub: bool = True
    version: str = LANGUAGE_SPEAKING_LEARNING_STAGE_VERSION


_STAGE_LABELS: dict[SpeakingLearningStage, str] = {
    SpeakingLearningStage.foundation: "Foundation",
    SpeakingLearningStage.developing: "Developing",
    SpeakingLearningStage.advanced: "Advanced",
}


def speaking_stage_label(*, official_cefr: str, stage: SpeakingLearningStage | int) -> str:
    """CEFR-relative student-safe stage label (e.g. ``A2 Foundation``)."""
    st = SpeakingLearningStage(max(1, min(3, int(stage))))
    cefr = (official_cefr or "A2").upper()
    return f"{cefr} {_STAGE_LABELS[st]}"


class DataSufficiencyVerdict(StrEnum):
    """Deterministic evidence-sufficiency band for stage signals."""

    insufficient = "insufficient"
    partial = "partial"
    sufficient = "sufficient"


class SpeakingStageBlockerKind(StrEnum):
    """Typed deterministic stage blockers — never invented by AI."""

    insufficient_evidence = "insufficient_evidence"
    low_curriculum_coverage = "low_curriculum_coverage"
    core_skill_gap = "core_skill_gap"
    unstable_performance = "unstable_performance"
    repeated_retry_dependence = "repeated_retry_dependence"
    high_retention_risk = "high_retention_risk"
    insufficient_transfer_evidence = "insufficient_transfer_evidence"
    too_many_at_risk_skills = "too_many_at_risk_skills"
    support_dependence_unknown = "support_dependence_unknown"


SUPPORT_DEPENDENCE_UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SpeakingStageBlocker:
    """One deterministic blocker for later S16 consumption."""

    kind: SpeakingStageBlockerKind
    severity: str  # info | warning | blocking
    student_safe_message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "severity": self.severity,
            "student_safe_message": self.student_safe_message,
        }


@dataclass(frozen=True, slots=True)
class SpeakingStageSignalSnapshot:
    """Deterministic curriculum-relative stage evidence aggregation (S15).

    Projection only. Does NOT decide stage transitions (S16) or mutate
    ``learning_stage_speaking`` / ``official_speaking_cefr`` / S2.
    """

    schema_version: str
    official_cefr: str
    current_stage: SpeakingLearningStage
    curriculum_skill_count: int
    skills_with_evidence_count: int
    coverage_ratio: float
    core_skill_coverage_ratio: float
    sufficient_evidence_ratio: float
    stable_skill_ratio: float
    developing_skill_ratio: float
    at_risk_skill_ratio: float
    in_level_mastery_avg: float
    in_level_stability_avg: float
    recent_success_signal: float
    recent_failure_signal: float
    retry_dependence_signal: float | None
    support_dependence_signal: str  # always "unknown" in S15
    retention_risk_signal: float
    transfer_breadth_signal: float
    context_diversity_signal: float
    performance_stability_signal: float
    data_sufficiency: DataSufficiencyVerdict
    blockers: tuple[SpeakingStageBlocker, ...]
    snapshot_fingerprint: str
    # Extra counts for sufficiency/explainability (internal).
    total_observations: int = 0
    distinct_tasks_attempted: int = 0
    core_skills_with_min_evidence: int = 0
    core_skill_count: int = 0

    def to_internal_dict(self) -> dict[str, object]:
        """Serialize for tests / S16 — NOT student UI."""
        return {
            "schema_version": self.schema_version,
            "official_cefr": self.official_cefr,
            "current_stage": int(self.current_stage),
            "current_stage_name": self.current_stage.name,
            "stage_label": speaking_stage_label(
                official_cefr=self.official_cefr, stage=self.current_stage
            ),
            "curriculum_skill_count": self.curriculum_skill_count,
            "skills_with_evidence_count": self.skills_with_evidence_count,
            "coverage_ratio": round(self.coverage_ratio, 4),
            "core_skill_coverage_ratio": round(self.core_skill_coverage_ratio, 4),
            "sufficient_evidence_ratio": round(self.sufficient_evidence_ratio, 4),
            "stable_skill_ratio": round(self.stable_skill_ratio, 4),
            "developing_skill_ratio": round(self.developing_skill_ratio, 4),
            "at_risk_skill_ratio": round(self.at_risk_skill_ratio, 4),
            "in_level_mastery_avg": round(self.in_level_mastery_avg, 4),
            "in_level_stability_avg": round(self.in_level_stability_avg, 4),
            "recent_success_signal": round(self.recent_success_signal, 4),
            "recent_failure_signal": round(self.recent_failure_signal, 4),
            "retry_dependence_signal": (
                None
                if self.retry_dependence_signal is None
                else round(self.retry_dependence_signal, 4)
            ),
            "support_dependence_signal": self.support_dependence_signal,
            "retention_risk_signal": round(self.retention_risk_signal, 4),
            "transfer_breadth_signal": round(self.transfer_breadth_signal, 4),
            "context_diversity_signal": round(self.context_diversity_signal, 4),
            "performance_stability_signal": round(self.performance_stability_signal, 4),
            "data_sufficiency": self.data_sufficiency.value,
            "blockers": [b.to_dict() for b in self.blockers],
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "total_observations": self.total_observations,
            "distinct_tasks_attempted": self.distinct_tasks_attempted,
            "core_skills_with_min_evidence": self.core_skills_with_min_evidence,
            "core_skill_count": self.core_skill_count,
        }
