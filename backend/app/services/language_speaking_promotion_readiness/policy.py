"""S17 speaking promotion-readiness policy thresholds + provenance.

S16 answers: may the student advance Developing → Advanced within CEFR?
S17 answers: is an Advanced student ready to attempt NEXT-CEFR assessment?

All numeric thresholds are provenance-labeled. Never claim curriculum-authored
speaking readiness policy exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.services.language_speaking_learning_stage.types import (
    DataSufficiencyVerdict,
    SpeakingStageBlockerKind,
)

LANGUAGE_SPEAKING_PROMOTION_READINESS_VERSION = "17.0.0"
READINESS_POLICY_VERSION = "17.0.0"
READINESS_SCHEMA_VERSION = "17.0.0"


class ThresholdSourceKind(StrEnum):
    product_policy_default = "PRODUCT_POLICY_DEFAULT"
    s15_reused = "S15_REUSED"
    listening_aligned_default = "LISTENING_ALIGNED_DEFAULT"


@dataclass(frozen=True, slots=True)
class ThresholdProvenance:
    policy_field: str
    value: str
    source_kind: ThresholdSourceKind
    note: str

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_field": self.policy_field,
            "value": self.value,
            "source_kind": self.source_kind.value,
            "note": self.note,
            "product_policy_default": self.source_kind is ThresholdSourceKind.product_policy_default,
            "s15_reused": self.source_kind is ThresholdSourceKind.s15_reused,
            "listening_aligned_default": self.source_kind
            is ThresholdSourceKind.listening_aligned_default,
        }


@dataclass(frozen=True, slots=True)
class SpeakingPromotionReadinessPolicy:
    """Global deterministic readiness policy (CEFR-relative evidence, global thresholds)."""

    policy_version: str
    # Status bands (score after hard blockers apply to contributions).
    promotion_available_score: int  # dual-gate candidate floor
    ready_score: int
    almost_ready_score: int
    # Eligibility
    require_advanced_stage: bool
    require_sufficient_data: bool
    require_known_retry: bool
    minimum_distinct_tasks: int
    # Hard blocker floors (exclusive upper bounds named explicitly).
    minimum_coverage_ratio: float
    minimum_core_coverage_ratio: float
    minimum_stable_skill_ratio: float
    minimum_sufficient_evidence_ratio: float
    minimum_in_level_mastery_avg: float
    minimum_performance_stability: float
    minimum_transfer_breadth: float
    minimum_context_diversity: float
    exclusive_maximum_at_risk_skill_ratio: float
    exclusive_maximum_retention_risk: float
    exclusive_maximum_retry_dependence: float
    maximum_recent_failure_signal: float  # inclusive <=
    hard_blocker_kinds: frozenset[SpeakingStageBlockerKind]
    dimension_weights: dict[str, float]
    provenance: tuple[ThresholdProvenance, ...]


def _p(
    field: str,
    value: str,
    kind: ThresholdSourceKind,
    note: str,
) -> ThresholdProvenance:
    return ThresholdProvenance(policy_field=field, value=value, source_kind=kind, note=note)


_WEIGHTS: dict[str, float] = {
    "advanced_stage": 0.10,
    "data_sufficiency": 0.10,
    "coverage": 0.12,
    "core_coverage": 0.10,
    "stable_skill_ratio": 0.12,
    "mastery": 0.10,
    "performance_stability": 0.08,
    "transfer": 0.08,
    "context_diversity": 0.06,
    "retention_inverse": 0.06,
    "retry_independence": 0.05,
    "recent_success": 0.03,
}


_PROVENANCE: tuple[ThresholdProvenance, ...] = (
    _p(
        "promotion_available_score",
        "90",
        ThresholdSourceKind.product_policy_default,
        "Dual-gate candidate floor; Listening used 100 — Speaking uses 90.",
    ),
    _p(
        "ready_score",
        "80",
        ThresholdSourceKind.listening_aligned_default,
        "Aligned to listening READY band.",
    ),
    _p(
        "almost_ready_score",
        "50",
        ThresholdSourceKind.listening_aligned_default,
        "Aligned to listening ALMOST_READY band.",
    ),
    _p(
        "require_sufficient_data",
        "sufficient",
        ThresholdSourceKind.s15_reused,
        "S15 DataSufficiencyVerdict.sufficient is eligibility floor for assessment readiness.",
    ),
    _p(
        "minimum_distinct_tasks",
        "2",
        ThresholdSourceKind.s15_reused,
        "S15 MIN_DISTINCT_TASKS — retry observability floor.",
    ),
    _p(
        "minimum_coverage_ratio",
        "0.50",
        ThresholdSourceKind.product_policy_default,
        "Stricter than S16 D→A 0.40 for next-CEFR assessment readiness.",
    ),
    _p(
        "minimum_core_coverage_ratio",
        "0.60",
        ThresholdSourceKind.product_policy_default,
        "Stricter than S16/S15 core gap 0.50.",
    ),
    _p(
        "minimum_stable_skill_ratio",
        "0.40",
        ThresholdSourceKind.product_policy_default,
        "Stricter than S16 D→A 0.35.",
    ),
    _p(
        "minimum_sufficient_evidence_ratio",
        "0.40",
        ThresholdSourceKind.product_policy_default,
        "Stricter than S16 D→A 0.35.",
    ),
    _p(
        "minimum_in_level_mastery_avg",
        "0.55",
        ThresholdSourceKind.product_policy_default,
        "Stricter than S16 D→A 0.50.",
    ),
    _p(
        "minimum_performance_stability",
        "0.45",
        ThresholdSourceKind.product_policy_default,
        "Stricter than S16/S15 stability floor 0.40.",
    ),
    _p(
        "minimum_transfer_breadth",
        "0.30",
        ThresholdSourceKind.product_policy_default,
        "Stricter than S16/S15 transfer floor 0.25.",
    ),
    _p(
        "minimum_context_diversity",
        "0.35",
        ThresholdSourceKind.product_policy_default,
        "Stricter than S16 D→A 0.30.",
    ),
    _p(
        "exclusive_maximum_at_risk_skill_ratio",
        "< 0.25",
        ThresholdSourceKind.product_policy_default,
        "Exclusive upper bound; stricter than S16 D→A < 0.30.",
    ),
    _p(
        "exclusive_maximum_retention_risk",
        "< 0.25",
        ThresholdSourceKind.product_policy_default,
        "Exclusive upper bound; stricter than S16 D→A < 0.30.",
    ),
    _p(
        "exclusive_maximum_retry_dependence",
        "< 0.45",
        ThresholdSourceKind.product_policy_default,
        "Exclusive upper bound; stricter than S16 D→A < 0.50.",
    ),
    _p(
        "maximum_recent_failure_signal",
        "<= 0.40",
        ThresholdSourceKind.product_policy_default,
        "Inclusive; stricter than S16 <= 0.45.",
    ),
    _p(
        "dimension_weights",
        str(_WEIGHTS),
        ThresholdSourceKind.product_policy_default,
        "Speaking-native weights summing to 1.0.",
    ),
)


DEFAULT_READINESS_POLICY = SpeakingPromotionReadinessPolicy(
    policy_version=READINESS_POLICY_VERSION,
    promotion_available_score=90,
    ready_score=80,
    almost_ready_score=50,
    require_advanced_stage=True,
    require_sufficient_data=True,
    require_known_retry=True,
    minimum_distinct_tasks=2,
    minimum_coverage_ratio=0.50,
    minimum_core_coverage_ratio=0.60,
    minimum_stable_skill_ratio=0.40,
    minimum_sufficient_evidence_ratio=0.40,
    minimum_in_level_mastery_avg=0.55,
    minimum_performance_stability=0.45,
    minimum_transfer_breadth=0.30,
    minimum_context_diversity=0.35,
    exclusive_maximum_at_risk_skill_ratio=0.25,
    exclusive_maximum_retention_risk=0.25,
    exclusive_maximum_retry_dependence=0.45,
    maximum_recent_failure_signal=0.40,
    hard_blocker_kinds=frozenset(
        {
            SpeakingStageBlockerKind.insufficient_evidence,
            SpeakingStageBlockerKind.low_curriculum_coverage,
            SpeakingStageBlockerKind.core_skill_gap,
            SpeakingStageBlockerKind.unstable_performance,
            SpeakingStageBlockerKind.repeated_retry_dependence,
            SpeakingStageBlockerKind.high_retention_risk,
            SpeakingStageBlockerKind.insufficient_transfer_evidence,
            SpeakingStageBlockerKind.too_many_at_risk_skills,
        }
    ),
    dimension_weights=_WEIGHTS,
    provenance=_PROVENANCE,
)

assert abs(sum(DEFAULT_READINESS_POLICY.dimension_weights.values()) - 1.0) < 1e-9
