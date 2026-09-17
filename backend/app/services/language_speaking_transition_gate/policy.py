"""S16 v1 global deterministic internal-stage transition policy.

Evidence is CEFR-relative (S15 snapshots). Thresholds are global stage-policy
defaults — NOT curriculum-derived transition rules. Future CEFR-specific
overrides may key by (official_cefr, from_stage, to_stage).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_learning_stage.types import (
    DataSufficiencyVerdict,
    SpeakingStageBlockerKind,
)
from app.services.language_speaking_transition_gate.types import TRANSITION_POLICY_VERSION


class ThresholdSourceKind(StrEnum):
    s15_signal_band = "s15_signal_band"
    s15_blocker_literal = "s15_blocker_literal"
    product_policy_default = "PRODUCT_POLICY_DEFAULT"
    not_required = "not_required"


@dataclass(frozen=True, slots=True)
class ThresholdProvenance:
    """Honest provenance for every S16 policy field."""

    policy_field: str
    proposed_value: str
    source: str
    reused_from_s15: bool
    semantic_validity: str
    risk_if_too_permissive: str
    risk_if_too_strict: str
    source_kind: ThresholdSourceKind
    upper_bound_exclusive: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_field": self.policy_field,
            "proposed_value": self.proposed_value,
            "source": self.source,
            "reused_from_s15": self.reused_from_s15,
            "semantic_validity": self.semantic_validity,
            "risk_if_too_permissive": self.risk_if_too_permissive,
            "risk_if_too_strict": self.risk_if_too_strict,
            "source_kind": self.source_kind.value,
            "product_policy_default": self.source_kind is ThresholdSourceKind.product_policy_default,
            "upper_bound_exclusive": self.upper_bound_exclusive,
        }


@dataclass(frozen=True, slots=True)
class SpeakingStageTransitionPolicy:
    """Global (from_stage → to_stage) internal-stage authorization policy."""

    policy_version: str
    from_stage: SpeakingLearningStage
    to_stage: SpeakingLearningStage
    scope: str  # "global_deterministic_internal_stage_policy"
    minimum_data_sufficiency: DataSufficiencyVerdict
    # Minimum floors use inclusive >= / == semantics.
    minimum_coverage_ratio: float
    minimum_core_coverage_ratio: float | None  # None = skip when core_skill_count==0
    minimum_stable_skill_ratio: float | None
    minimum_in_level_mastery_avg: float | None
    minimum_sufficient_evidence_ratio: float | None
    minimum_performance_stability: float | None
    minimum_transfer_breadth: float | None
    minimum_context_diversity: float | None
    minimum_distinct_tasks_attempted: int | None
    require_known_retry_dependence: bool
    # Exclusive upper bounds use strict < (documented; never implement as <=).
    exclusive_maximum_at_risk_skill_ratio: float | None
    exclusive_maximum_retention_risk: float | None
    exclusive_maximum_retry_dependence: float | None
    # Inclusive upper bound (allowed at equality).
    maximum_recent_failure_signal: float | None
    hard_blocker_kinds: frozenset[SpeakingStageBlockerKind]
    advisory_blocker_kinds: frozenset[SpeakingStageBlockerKind]
    provenance: tuple[ThresholdProvenance, ...]


def _prov(
    *,
    field: str,
    value: str,
    source: str,
    reused: bool,
    validity: str,
    permissive: str,
    strict: str,
    kind: ThresholdSourceKind,
    exclusive: bool = False,
) -> ThresholdProvenance:
    return ThresholdProvenance(
        policy_field=field,
        proposed_value=value,
        source=source,
        reused_from_s15=reused,
        semantic_validity=validity,
        risk_if_too_permissive=permissive,
        risk_if_too_strict=strict,
        source_kind=kind,
        upper_bound_exclusive=exclusive,
    )


_FD_PROVENANCE: tuple[ThresholdProvenance, ...] = (
    _prov(
        field="minimum_data_sufficiency",
        value="partial",
        source="DataSufficiencyVerdict.partial",
        reused=True,
        validity="Partial means enough CEFR-relative evidence to leave sparse-entry state.",
        permissive="Advances from noisy evidence.",
        strict="Early learners stay Foundation too long.",
        kind=ThresholdSourceKind.s15_signal_band,
    ),
    _prov(
        field="minimum_coverage_ratio",
        value="0.25",
        source="S15 COVERAGE_PARTIAL_RATIO",
        reused=True,
        validity="S15 boundary for meaningful in-level curriculum coverage.",
        permissive="Narrow cluster may advance.",
        strict="Blocked before broad sampling is realistic.",
        kind=ThresholdSourceKind.s15_signal_band,
    ),
    _prov(
        field="minimum_core_coverage_ratio",
        value="0.50",
        source="S15 core_skill_gap blocker literal",
        reused=True,
        validity="Core skill gap is already a blocking S15 educational concern.",
        permissive="Core gaps hidden by non-core practice.",
        strict="Core-heavy CEFRs may slow advancement.",
        kind=ThresholdSourceKind.s15_blocker_literal,
    ),
    _prov(
        field="minimum_in_level_mastery_avg",
        value="0.35",
        source="PRODUCT POLICY DEFAULT",
        reused=False,
        validity="No authoritative transition policy; distinguishes weak exposure from usable early performance.",
        permissive="Weak performance advances.",
        strict="Repeats Foundation despite adequate early growth.",
        kind=ThresholdSourceKind.product_policy_default,
    ),
    _prov(
        field="minimum_stable_skill_ratio",
        value="0.15",
        source="PRODUCT POLICY DEFAULT",
        reused=False,
        validity="Prevents advancing on one isolated successful skill.",
        permissive="Single-skill excellence may advance.",
        strict="Small curricula may over-block.",
        kind=ThresholdSourceKind.product_policy_default,
    ),
    _prov(
        field="exclusive_maximum_at_risk_skill_ratio",
        value="< 0.35",
        source="S15 AT_RISK_SHARE_BLOCK_THRESHOLD (exclusive upper bound for transition)",
        reused=True,
        validity="S15 says this much at-risk evidence is a blocking educational concern.",
        permissive="Too many fragile skills advance.",
        strict="Blocked by a few recoverable weak spots.",
        kind=ThresholdSourceKind.s15_blocker_literal,
        exclusive=True,
    ),
    _prov(
        field="minimum_context_diversity",
        value="NOT_REQUIRED",
        source="Audit: no curriculum transition policy requires F→D context diversity",
        reused=False,
        validity="Foundation is acquisition/stabilization; transfer breadth reserved for D→A.",
        permissive="May advance with narrow contexts.",
        strict="N/A — not required.",
        kind=ThresholdSourceKind.not_required,
    ),
    _prov(
        field="retry_dependence",
        value="NOT_REQUIRED; UNKNOWN allowed",
        source="Audit: Foundation exit may precede meaningful S11 lineage",
        reused=False,
        validity="Do not invent independence from absent attempt evidence for early stage exit.",
        permissive="Retry dependence may be missed early.",
        strict="N/A — unknown allowed.",
        kind=ThresholdSourceKind.not_required,
    ),
)

_DA_PROVENANCE: tuple[ThresholdProvenance, ...] = (
    _prov(
        field="minimum_data_sufficiency",
        value="sufficient",
        source="DataSufficiencyVerdict.sufficient",
        reused=True,
        validity="Advanced is promotion-readiness-adjacent; sufficient is minimum reliable evidence floor.",
        permissive="Advanced from partial evidence.",
        strict="Strong learners with incomplete telemetry delayed.",
        kind=ThresholdSourceKind.s15_signal_band,
    ),
    _prov(
        field="minimum_coverage_ratio",
        value="0.40",
        source="S15 COVERAGE_SUFFICIENT_RATIO",
        reused=True,
        validity="S15 sufficient coverage as broad in-level evidence floor.",
        permissive="Narrow coverage advances.",
        strict="Broad curricula may require many sessions.",
        kind=ThresholdSourceKind.s15_signal_band,
    ),
    _prov(
        field="minimum_core_coverage_ratio",
        value="0.50",
        source="S15 core_skill_gap blocker literal",
        reused=True,
        validity="Advanced must not ignore unresolved core-skill gaps.",
        permissive="Non-core strengths mask core weakness.",
        strict="Core-heavy levels feel sticky.",
        kind=ThresholdSourceKind.s15_blocker_literal,
    ),
    _prov(
        field="minimum_sufficient_evidence_ratio",
        value="0.35",
        source="PRODUCT POLICY DEFAULT",
        reused=False,
        validity="Ensures enough skills meet catalog evidence minimums.",
        permissive="Shallow evidence across many skills advances.",
        strict="Requires more repeated observations.",
        kind=ThresholdSourceKind.product_policy_default,
    ),
    _prov(
        field="minimum_stable_skill_ratio",
        value="0.35",
        source="PRODUCT POLICY DEFAULT",
        reused=False,
        validity="Prevents one-skill / few-skill advancement to Advanced.",
        permissive="Isolated stability advances.",
        strict="Extra stabilization work needed.",
        kind=ThresholdSourceKind.product_policy_default,
    ),
    _prov(
        field="minimum_in_level_mastery_avg",
        value="0.50",
        source="PRODUCT POLICY DEFAULT",
        reused=False,
        validity="Usable mid-level mastery before Advanced.",
        permissive="Mediocre mastery advances.",
        strict="Stable but mid-scoring learners held.",
        kind=ThresholdSourceKind.product_policy_default,
    ),
    _prov(
        field="exclusive_maximum_at_risk_skill_ratio",
        value="< 0.30",
        source="PRODUCT POLICY DEFAULT (stricter than S15 0.35)",
        reused=False,
        validity="Advanced tolerates less unresolved risk than S15 blocker detection.",
        permissive="Fragile skills enter Advanced.",
        strict="Minor risk clusters delay advancement.",
        kind=ThresholdSourceKind.product_policy_default,
        exclusive=True,
    ),
    _prov(
        field="minimum_performance_stability",
        value="0.40",
        source="S15 STABILITY_LOW_THRESHOLD",
        reused=True,
        validity="Below this S15 marks unstable; valid hard-block for Advanced.",
        permissive="Volatile performance advances.",
        strict="Uneven recent history delays.",
        kind=ThresholdSourceKind.s15_signal_band,
    ),
    _prov(
        field="maximum_recent_failure_signal",
        value="<= 0.45",
        source="PRODUCT POLICY DEFAULT",
        reused=False,
        validity="Prevents recent decline being hidden by lifetime state; inclusive at boundary.",
        permissive="Recent failures ignored.",
        strict="Recoverable setbacks over-block.",
        kind=ThresholdSourceKind.product_policy_default,
    ),
    _prov(
        field="exclusive_maximum_retention_risk",
        value="< 0.30",
        source="PRODUCT POLICY DEFAULT (stricter than S15 0.35)",
        reused=False,
        validity="Advanced requires stronger retention than generic S15 risk detection.",
        permissive="Rusty skills advance.",
        strict="Review needs delay advancement.",
        kind=ThresholdSourceKind.product_policy_default,
        exclusive=True,
    ),
    _prov(
        field="minimum_distinct_tasks_attempted",
        value="2",
        source="S15 MIN_DISTINCT_TASKS + require_known_retry_dependence",
        reused=True,
        validity="Observability floor so UNKNOWN retry is not treated as independence.",
        permissive="Unknown independence treated as acceptable.",
        strict="Students lacking S11 lineage cannot reach Advanced yet.",
        kind=ThresholdSourceKind.s15_signal_band,
    ),
    _prov(
        field="require_known_retry_dependence",
        value="True",
        source="Policy review option A+B: Advanced requires retry observability",
        reused=False,
        validity="Do not collapse UNKNOWN retry into pass for promotion-readiness-adjacent stage.",
        permissive="Silent UNKNOWN as independence.",
        strict="No S11 lineage blocks Advanced.",
        kind=ThresholdSourceKind.product_policy_default,
    ),
    _prov(
        field="exclusive_maximum_retry_dependence",
        value="< 0.50",
        source="PRODUCT POLICY DEFAULT (stricter than S15 0.55)",
        reused=False,
        validity="Advanced requires stronger independence than S15 repeated-retry warning.",
        permissive="Retry-dependent learners advance.",
        strict="Demands too much first-pass independence.",
        kind=ThresholdSourceKind.product_policy_default,
        exclusive=True,
    ),
    _prov(
        field="minimum_transfer_breadth",
        value="0.25",
        source="S15 transfer blocker floor",
        reused=True,
        validity="Transfer is materially relevant for Advanced.",
        permissive="Narrow-context mastery advances.",
        strict="Transfer evidence becomes a bottleneck.",
        kind=ThresholdSourceKind.s15_blocker_literal,
    ),
    _prov(
        field="minimum_context_diversity",
        value="0.30",
        source="PRODUCT POLICY DEFAULT",
        reused=False,
        validity="Breadth matters near Advanced; no internal-stage curriculum threshold existed.",
        permissive="Over-specialized practice advances.",
        strict="Extra varied contexts needed.",
        kind=ThresholdSourceKind.product_policy_default,
    ),
)


FOUNDATION_TO_DEVELOPING = SpeakingStageTransitionPolicy(
    policy_version=TRANSITION_POLICY_VERSION,
    from_stage=SpeakingLearningStage.foundation,
    to_stage=SpeakingLearningStage.developing,
    scope="global_deterministic_internal_stage_policy",
    minimum_data_sufficiency=DataSufficiencyVerdict.partial,
    minimum_coverage_ratio=0.25,
    minimum_core_coverage_ratio=0.50,
    minimum_stable_skill_ratio=0.15,
    minimum_in_level_mastery_avg=0.35,
    minimum_sufficient_evidence_ratio=None,
    minimum_performance_stability=None,
    minimum_transfer_breadth=None,
    minimum_context_diversity=None,  # NOT_REQUIRED for F→D
    minimum_distinct_tasks_attempted=None,
    require_known_retry_dependence=False,
    exclusive_maximum_at_risk_skill_ratio=0.35,  # pass iff < 0.35
    exclusive_maximum_retention_risk=None,
    exclusive_maximum_retry_dependence=None,
    maximum_recent_failure_signal=None,
    hard_blocker_kinds=frozenset(
        {
            SpeakingStageBlockerKind.insufficient_evidence,
            SpeakingStageBlockerKind.low_curriculum_coverage,
            SpeakingStageBlockerKind.core_skill_gap,
            SpeakingStageBlockerKind.too_many_at_risk_skills,
        }
    ),
    advisory_blocker_kinds=frozenset(
        {
            SpeakingStageBlockerKind.unstable_performance,
            SpeakingStageBlockerKind.repeated_retry_dependence,
            SpeakingStageBlockerKind.high_retention_risk,
            SpeakingStageBlockerKind.support_dependence_unknown,
        }
    ),
    provenance=_FD_PROVENANCE,
)


DEVELOPING_TO_ADVANCED = SpeakingStageTransitionPolicy(
    policy_version=TRANSITION_POLICY_VERSION,
    from_stage=SpeakingLearningStage.developing,
    to_stage=SpeakingLearningStage.advanced,
    scope="global_deterministic_internal_stage_policy",
    minimum_data_sufficiency=DataSufficiencyVerdict.sufficient,
    minimum_coverage_ratio=0.40,
    minimum_core_coverage_ratio=0.50,
    minimum_stable_skill_ratio=0.35,
    minimum_in_level_mastery_avg=0.50,
    minimum_sufficient_evidence_ratio=0.35,
    minimum_performance_stability=0.40,
    minimum_transfer_breadth=0.25,
    minimum_context_diversity=0.30,
    minimum_distinct_tasks_attempted=2,
    require_known_retry_dependence=True,
    exclusive_maximum_at_risk_skill_ratio=0.30,  # pass iff < 0.30
    exclusive_maximum_retention_risk=0.30,  # pass iff < 0.30
    exclusive_maximum_retry_dependence=0.50,  # pass iff < 0.50
    maximum_recent_failure_signal=0.45,  # pass iff <= 0.45
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
    advisory_blocker_kinds=frozenset(
        {
            SpeakingStageBlockerKind.support_dependence_unknown,
        }
    ),
    provenance=_DA_PROVENANCE,
)


# Global defaults keyed by (from_stage, to_stage). Future: (cefr, from, to).
GATE_POLICIES: dict[tuple[SpeakingLearningStage, SpeakingLearningStage], SpeakingStageTransitionPolicy] = {
    (SpeakingLearningStage.foundation, SpeakingLearningStage.developing): FOUNDATION_TO_DEVELOPING,
    (SpeakingLearningStage.developing, SpeakingLearningStage.advanced): DEVELOPING_TO_ADVANCED,
}


def policy_for_transition(
    from_stage: SpeakingLearningStage,
    to_stage: SpeakingLearningStage,
    *,
    official_cefr: str | None = None,  # reserved for future CEFR overrides
) -> SpeakingStageTransitionPolicy | None:
    """Resolve policy. official_cefr ignored in S16 v1 (global defaults only)."""
    _ = official_cefr  # future override hook
    return GATE_POLICIES.get((from_stage, to_stage))


def all_product_policy_default_fields() -> tuple[str, ...]:
    """Fields explicitly labeled PRODUCT POLICY DEFAULT in provenance."""
    fields: list[str] = []
    for policy in GATE_POLICIES.values():
        for p in policy.provenance:
            if p.source_kind is ThresholdSourceKind.product_policy_default:
                fields.append(f"{policy.from_stage.name}->{policy.to_stage.name}:{p.policy_field}")
    return tuple(fields)
