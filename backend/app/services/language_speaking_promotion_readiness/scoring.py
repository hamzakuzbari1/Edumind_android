"""Pure speaking promotion readiness scoring (S17)."""

from __future__ import annotations

from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_learning_stage.types import (
    DataSufficiencyVerdict,
    SpeakingStageBlockerKind,
    SpeakingStageSignalSnapshot,
    SUPPORT_DEPENDENCE_UNKNOWN,
)
from app.services.language_speaking_promotion_readiness.policy import (
    DEFAULT_READINESS_POLICY,
    READINESS_POLICY_VERSION,
    READINESS_SCHEMA_VERSION,
    SpeakingPromotionReadinessPolicy,
)
from app.services.language_speaking_promotion_readiness.target_cefr import (
    NextCefrResolutionError,
    resolve_next_speaking_cefr,
)
from app.services.language_speaking_promotion_readiness.types import (
    SpeakingPromotionReadinessResult,
    SpeakingReadinessDimensionScore,
    SpeakingReadinessStatus,
    SpeakingUnlockState,
    finalize_readiness_fingerprint,
)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _dim(
    code: str,
    *,
    current: float,
    required: float,
    weight: float,
    higher_is_better: bool = True,
) -> SpeakingReadinessDimensionScore:
    if higher_is_better:
        progress = _clamp01(current / required) if required > 0 else 0.0
        passed = current >= required
    else:
        # current is a risk; required is exclusive max — progress high when risk low
        progress = _clamp01(1.0 - (current / required)) if required > 0 else 0.0
        passed = current < required
    contribution = progress * weight * 100.0
    return SpeakingReadinessDimensionScore(
        code=code,
        current=current,
        required=required,
        progress=progress,
        weight=weight,
        contribution=contribution,
        passed=passed,
    )


def _status_for_score(score: int, policy: SpeakingPromotionReadinessPolicy) -> SpeakingReadinessStatus:
    if score >= policy.promotion_available_score:
        return SpeakingReadinessStatus.promotion_available_candidate
    if score >= policy.ready_score:
        return SpeakingReadinessStatus.ready
    if score >= policy.almost_ready_score:
        return SpeakingReadinessStatus.almost_ready
    return SpeakingReadinessStatus.not_ready


def apply_dual_gate_unlock(
    result: SpeakingPromotionReadinessResult,
    *,
    stability_requirements_passed: bool,
) -> SpeakingPromotionReadinessResult:
    """Finalize unlock: score floor AND empty hard blockers AND independent stability pass."""
    score_ok = result.readiness_score >= DEFAULT_READINESS_POLICY.promotion_available_score
    blockers_empty = len(result.hard_blockers) == 0 and result.eligible_for_readiness
    unlocked = score_ok and blockers_empty and stability_requirements_passed

    if not result.eligible_for_readiness:
        unlock_state = SpeakingUnlockState.locked
    elif unlocked:
        unlock_state = SpeakingUnlockState.unlocked
    elif score_ok and blockers_empty and not stability_requirements_passed:
        unlock_state = SpeakingUnlockState.ready_to_unlock
    elif result.current_stage is SpeakingLearningStage.advanced:
        unlock_state = SpeakingUnlockState.readiness_building
    else:
        unlock_state = SpeakingUnlockState.locked

    updated = SpeakingPromotionReadinessResult(
        schema_version=result.schema_version,
        policy_version=result.policy_version,
        official_cefr=result.official_cefr,
        target_cefr=result.target_cefr,
        current_stage=result.current_stage,
        eligible_for_readiness=result.eligible_for_readiness,
        readiness_score=result.readiness_score,
        status=result.status,
        hard_blockers=result.hard_blockers,
        advisory_signals=result.advisory_signals,
        unknown_signals=result.unknown_signals,
        dimensions=result.dimensions,
        source_stage_signal_fingerprint=result.source_stage_signal_fingerprint,
        snapshot_fingerprint="",
        estimated_remaining=result.estimated_remaining,
        hard_blockers_empty=blockers_empty,
        score_meets_promotion_floor=score_ok,
        stability_requirements_passed=stability_requirements_passed,
        spa_unlocked=unlocked,
        unlock_state=unlock_state,
        strengths=result.strengths,
        next_actions=result.next_actions,
    )
    return finalize_readiness_fingerprint(updated)


def evaluate_speaking_promotion_readiness(
    snapshot: SpeakingStageSignalSnapshot,
    *,
    policy: SpeakingPromotionReadinessPolicy = DEFAULT_READINESS_POLICY,
) -> SpeakingPromotionReadinessResult:
    """Pure readiness evaluation from an S15 snapshot (stability not yet applied)."""
    stage = SpeakingLearningStage(int(snapshot.current_stage))
    official = (snapshot.official_cefr or "A2").upper()

    # Target CEFR resolution
    target: str | None = None
    blockers: list[str] = []
    try:
        target = resolve_next_speaking_cefr(official)
    except NextCefrResolutionError as exc:
        if exc.code == "terminal_c2":
            return finalize_readiness_fingerprint(
                SpeakingPromotionReadinessResult(
                    schema_version=READINESS_SCHEMA_VERSION,
                    policy_version=policy.policy_version,
                    official_cefr=official,
                    target_cefr=None,
                    current_stage=stage,
                    eligible_for_readiness=False,
                    readiness_score=0,
                    status=SpeakingReadinessStatus.blocked,
                    hard_blockers=("terminal_c2",),
                    advisory_signals=("already_at_c2",),
                    unknown_signals=(),
                    dimensions=(),
                    source_stage_signal_fingerprint=snapshot.snapshot_fingerprint,
                    snapshot_fingerprint="",
                    estimated_remaining=100.0,
                    hard_blockers_empty=False,
                    score_meets_promotion_floor=False,
                    stability_requirements_passed=False,
                    spa_unlocked=False,
                    unlock_state=SpeakingUnlockState.locked,
                    strengths=(),
                    next_actions=("You are already at the highest speaking CEFR band.",),
                )
            )
        blockers.append(exc.code)

    # Eligibility
    if policy.require_advanced_stage and stage is not SpeakingLearningStage.advanced:
        blockers.append("not_advanced_stage")
    if policy.require_sufficient_data and snapshot.data_sufficiency is not DataSufficiencyVerdict.sufficient:
        blockers.append("insufficient_data_sufficiency")
    if policy.require_known_retry and snapshot.retry_dependence_signal is None:
        blockers.append("retry_dependence_unknown")
    if snapshot.distinct_tasks_attempted < policy.minimum_distinct_tasks:
        blockers.append("insufficient_distinct_tasks")

    # Metric hard blockers (exclusive upper bounds use <)
    if snapshot.coverage_ratio < policy.minimum_coverage_ratio:
        blockers.append("low_coverage")
    if snapshot.core_skill_count > 0 and snapshot.core_skill_coverage_ratio < policy.minimum_core_coverage_ratio:
        blockers.append("core_coverage_gap")
    if snapshot.stable_skill_ratio < policy.minimum_stable_skill_ratio:
        blockers.append("low_stable_skill_ratio")
    if snapshot.sufficient_evidence_ratio < policy.minimum_sufficient_evidence_ratio:
        blockers.append("low_sufficient_evidence_ratio")
    if snapshot.in_level_mastery_avg < policy.minimum_in_level_mastery_avg:
        blockers.append("low_mastery")
    if snapshot.performance_stability_signal < policy.minimum_performance_stability:
        blockers.append("low_performance_stability")
    if snapshot.transfer_breadth_signal < policy.minimum_transfer_breadth:
        blockers.append("low_transfer_breadth")
    if snapshot.context_diversity_signal < policy.minimum_context_diversity:
        blockers.append("low_context_diversity")
    if snapshot.at_risk_skill_ratio >= policy.exclusive_maximum_at_risk_skill_ratio:
        blockers.append("too_many_at_risk_skills")
    if snapshot.retention_risk_signal >= policy.exclusive_maximum_retention_risk:
        blockers.append("high_retention_risk")
    if (
        snapshot.retry_dependence_signal is not None
        and snapshot.retry_dependence_signal >= policy.exclusive_maximum_retry_dependence
    ):
        blockers.append("high_retry_dependence")
    if snapshot.recent_failure_signal > policy.maximum_recent_failure_signal:
        blockers.append("high_recent_failure")

    present_kinds = {b.kind for b in snapshot.blockers}
    for kind in sorted(policy.hard_blocker_kinds, key=lambda k: k.value):
        if kind in present_kinds:
            blockers.append(f"blocker:{kind.value}")

    # Deduplicate preserving order
    seen: set[str] = set()
    hard = []
    for b in blockers:
        if b not in seen:
            seen.add(b)
            hard.append(b)

    advisory: list[str] = []
    unknown: list[str] = []
    if snapshot.support_dependence_signal == SUPPORT_DEPENDENCE_UNKNOWN or any(
        b.kind is SpeakingStageBlockerKind.support_dependence_unknown for b in snapshot.blockers
    ):
        unknown.append("support_dependence")
        advisory.append("support_dependence_unknown")

    eligible_for_readiness = stage is SpeakingLearningStage.advanced and target is not None

    w = policy.dimension_weights
    dims = [
        _dim(
            "advanced_stage",
            current=1.0 if stage is SpeakingLearningStage.advanced else 0.0,
            required=1.0,
            weight=w["advanced_stage"],
        ),
        _dim(
            "data_sufficiency",
            current=1.0
            if snapshot.data_sufficiency is DataSufficiencyVerdict.sufficient
            else (0.5 if snapshot.data_sufficiency is DataSufficiencyVerdict.partial else 0.0),
            required=1.0,
            weight=w["data_sufficiency"],
        ),
        _dim("coverage", current=snapshot.coverage_ratio, required=policy.minimum_coverage_ratio, weight=w["coverage"]),
        _dim(
            "core_coverage",
            current=snapshot.core_skill_coverage_ratio if snapshot.core_skill_count > 0 else 1.0,
            required=policy.minimum_core_coverage_ratio if snapshot.core_skill_count > 0 else 1.0,
            weight=w["core_coverage"],
        ),
        _dim(
            "stable_skill_ratio",
            current=snapshot.stable_skill_ratio,
            required=policy.minimum_stable_skill_ratio,
            weight=w["stable_skill_ratio"],
        ),
        _dim(
            "mastery",
            current=snapshot.in_level_mastery_avg,
            required=policy.minimum_in_level_mastery_avg,
            weight=w["mastery"],
        ),
        _dim(
            "performance_stability",
            current=snapshot.performance_stability_signal,
            required=policy.minimum_performance_stability,
            weight=w["performance_stability"],
        ),
        _dim(
            "transfer",
            current=snapshot.transfer_breadth_signal,
            required=policy.minimum_transfer_breadth,
            weight=w["transfer"],
        ),
        _dim(
            "context_diversity",
            current=snapshot.context_diversity_signal,
            required=policy.minimum_context_diversity,
            weight=w["context_diversity"],
        ),
        _dim(
            "retention_inverse",
            current=snapshot.retention_risk_signal,
            required=policy.exclusive_maximum_retention_risk,
            weight=w["retention_inverse"],
            higher_is_better=False,
        ),
        _dim(
            "retry_independence",
            current=(
                0.0
                if snapshot.retry_dependence_signal is None
                else snapshot.retry_dependence_signal
            ),
            required=policy.exclusive_maximum_retry_dependence,
            weight=w["retry_independence"],
            higher_is_better=False,
        ),
        _dim(
            "recent_success",
            current=snapshot.recent_success_signal,
            required=0.55,  # PRODUCT POLICY DEFAULT soft target for contribution only
            weight=w["recent_success"],
        ),
    ]

    raw_score = sum(d.contribution for d in dims)
    score = int(round(max(0.0, min(100.0, raw_score))))
    if not eligible_for_readiness:
        score = min(score, policy.almost_ready_score - 1)
        status = SpeakingReadinessStatus.blocked if stage is not SpeakingLearningStage.advanced else SpeakingReadinessStatus.not_ready
    else:
        status = _status_for_score(score, policy)

    strengths = tuple(d.code for d in dims if d.passed)
    next_actions: tuple[str, ...]
    if hard:
        next_actions = ("Strengthen weak speaking evidence before assessment readiness.",)
    elif score < policy.promotion_available_score:
        next_actions = ("Keep practicing for broader, more consistent speaking evidence.",)
    else:
        next_actions = ("Maintain consistency across a few more sessions.",)

    # Provisional unlock fields — stability applied later via apply_dual_gate_unlock.
    provisional = SpeakingPromotionReadinessResult(
        schema_version=READINESS_SCHEMA_VERSION,
        policy_version=policy.policy_version,
        official_cefr=official,
        target_cefr=target,
        current_stage=stage,
        eligible_for_readiness=eligible_for_readiness,
        readiness_score=score,
        status=status,
        hard_blockers=tuple(hard),
        advisory_signals=tuple(advisory),
        unknown_signals=tuple(unknown),
        dimensions=tuple(dims),
        source_stage_signal_fingerprint=snapshot.snapshot_fingerprint,
        snapshot_fingerprint="",
        estimated_remaining=round(max(0.0, 100.0 - score), 1),
        hard_blockers_empty=len(hard) == 0 and eligible_for_readiness,
        score_meets_promotion_floor=score >= policy.promotion_available_score,
        stability_requirements_passed=False,
        spa_unlocked=False,
        unlock_state=SpeakingUnlockState.locked,
        strengths=strengths,
        next_actions=next_actions,
    )
    return apply_dual_gate_unlock(provisional, stability_requirements_passed=False)
