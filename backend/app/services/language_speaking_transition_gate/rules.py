"""Pure deterministic speaking stage transition evaluator (S16).

Never writes learning_stage_speaking / official_speaking_cefr / promotion / S2.
No AI.
"""

from __future__ import annotations

from dataclasses import replace

from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_learning_stage.types import (
    DataSufficiencyVerdict,
    SpeakingStageBlockerKind,
    SpeakingStageSignalSnapshot,
)
from app.services.language_speaking_transition_gate.fingerprint import compute_decision_fingerprint
from app.services.language_speaking_transition_gate.policy import (
    SpeakingStageTransitionPolicy,
    policy_for_transition,
)
from app.services.language_speaking_transition_gate.types import (
    TRANSITION_GATE_SCHEMA_VERSION,
    TRANSITION_POLICY_VERSION,
    ComparisonOperator,
    SpeakingStageRequirementResult,
    SpeakingStageTransitionDecision,
    SpeakingStageTransitionDecisionKind,
)

_SUFFICIENCY_ORDER = {
    DataSufficiencyVerdict.insufficient: 0,
    DataSufficiencyVerdict.partial: 1,
    DataSufficiencyVerdict.sufficient: 2,
}


def _req(
    code: str,
    *,
    passed: bool,
    current: str,
    required: str,
    operator: ComparisonOperator,
    applicability: str = "required",
) -> SpeakingStageRequirementResult:
    return SpeakingStageRequirementResult(
        code=code,
        passed=passed,
        current=current,
        required=required,
        operator=operator,
        applicability=applicability,
    )


def _fmt(v: float | None) -> str:
    if v is None:
        return "None"
    return f"{v:.4f}"


def _evaluate_policy(
    snapshot: SpeakingStageSignalSnapshot,
    policy: SpeakingStageTransitionPolicy,
) -> list[SpeakingStageRequirementResult]:
    reqs: list[SpeakingStageRequirementResult] = []

    # Data sufficiency — minimum band (inclusive of that band and above).
    order_ok = _SUFFICIENCY_ORDER[snapshot.data_sufficiency] >= _SUFFICIENCY_ORDER[policy.minimum_data_sufficiency]
    reqs.append(
        _req(
            "minimum_data_sufficiency",
            passed=order_ok,
            current=snapshot.data_sufficiency.value,
            required=policy.minimum_data_sufficiency.value,
            operator=ComparisonOperator.ge,
        )
    )

    reqs.append(
        _req(
            "minimum_coverage_ratio",
            passed=snapshot.coverage_ratio >= policy.minimum_coverage_ratio,
            current=_fmt(snapshot.coverage_ratio),
            required=_fmt(policy.minimum_coverage_ratio),
            operator=ComparisonOperator.ge,
        )
    )

    # Core coverage — NOT_APPLICABLE when no core skills.
    if policy.minimum_core_coverage_ratio is None or snapshot.core_skill_count <= 0:
        reqs.append(
            _req(
                "minimum_core_coverage_ratio",
                passed=True,
                current=_fmt(snapshot.core_skill_coverage_ratio),
                required="NOT_APPLICABLE",
                operator=ComparisonOperator.absent,
                applicability="not_applicable",
            )
        )
    else:
        reqs.append(
            _req(
                "minimum_core_coverage_ratio",
                passed=snapshot.core_skill_coverage_ratio >= policy.minimum_core_coverage_ratio,
                current=_fmt(snapshot.core_skill_coverage_ratio),
                required=_fmt(policy.minimum_core_coverage_ratio),
                operator=ComparisonOperator.ge,
            )
        )

    if policy.minimum_stable_skill_ratio is not None:
        reqs.append(
            _req(
                "minimum_stable_skill_ratio",
                passed=snapshot.stable_skill_ratio >= policy.minimum_stable_skill_ratio,
                current=_fmt(snapshot.stable_skill_ratio),
                required=_fmt(policy.minimum_stable_skill_ratio),
                operator=ComparisonOperator.ge,
            )
        )

    if policy.minimum_in_level_mastery_avg is not None:
        reqs.append(
            _req(
                "minimum_in_level_mastery_avg",
                passed=snapshot.in_level_mastery_avg >= policy.minimum_in_level_mastery_avg,
                current=_fmt(snapshot.in_level_mastery_avg),
                required=_fmt(policy.minimum_in_level_mastery_avg),
                operator=ComparisonOperator.ge,
            )
        )

    if policy.minimum_sufficient_evidence_ratio is not None:
        reqs.append(
            _req(
                "minimum_sufficient_evidence_ratio",
                passed=snapshot.sufficient_evidence_ratio >= policy.minimum_sufficient_evidence_ratio,
                current=_fmt(snapshot.sufficient_evidence_ratio),
                required=_fmt(policy.minimum_sufficient_evidence_ratio),
                operator=ComparisonOperator.ge,
            )
        )

    if policy.minimum_performance_stability is not None:
        reqs.append(
            _req(
                "minimum_performance_stability",
                passed=snapshot.performance_stability_signal >= policy.minimum_performance_stability,
                current=_fmt(snapshot.performance_stability_signal),
                required=_fmt(policy.minimum_performance_stability),
                operator=ComparisonOperator.ge,
            )
        )

    if policy.maximum_recent_failure_signal is not None:
        # Inclusive upper bound: pass iff <= max.
        reqs.append(
            _req(
                "maximum_recent_failure_signal",
                passed=snapshot.recent_failure_signal <= policy.maximum_recent_failure_signal,
                current=_fmt(snapshot.recent_failure_signal),
                required=_fmt(policy.maximum_recent_failure_signal),
                operator=ComparisonOperator.le,
            )
        )

    # Exclusive upper bounds — pass iff current < threshold (never <=).
    if policy.exclusive_maximum_at_risk_skill_ratio is not None:
        reqs.append(
            _req(
                "exclusive_maximum_at_risk_skill_ratio",
                passed=snapshot.at_risk_skill_ratio < policy.exclusive_maximum_at_risk_skill_ratio,
                current=_fmt(snapshot.at_risk_skill_ratio),
                required=f"< {_fmt(policy.exclusive_maximum_at_risk_skill_ratio)}",
                operator=ComparisonOperator.lt,
            )
        )

    if policy.exclusive_maximum_retention_risk is not None:
        reqs.append(
            _req(
                "exclusive_maximum_retention_risk",
                passed=snapshot.retention_risk_signal < policy.exclusive_maximum_retention_risk,
                current=_fmt(snapshot.retention_risk_signal),
                required=f"< {_fmt(policy.exclusive_maximum_retention_risk)}",
                operator=ComparisonOperator.lt,
            )
        )

    # Context diversity — NOT_APPLICABLE when policy has None.
    if policy.minimum_context_diversity is None:
        reqs.append(
            _req(
                "minimum_context_diversity",
                passed=True,
                current=_fmt(snapshot.context_diversity_signal),
                required="NOT_REQUIRED",
                operator=ComparisonOperator.absent,
                applicability="not_applicable",
            )
        )
    else:
        reqs.append(
            _req(
                "minimum_context_diversity",
                passed=snapshot.context_diversity_signal >= policy.minimum_context_diversity,
                current=_fmt(snapshot.context_diversity_signal),
                required=_fmt(policy.minimum_context_diversity),
                operator=ComparisonOperator.ge,
            )
        )

    if policy.minimum_transfer_breadth is None:
        reqs.append(
            _req(
                "minimum_transfer_breadth",
                passed=True,
                current=_fmt(snapshot.transfer_breadth_signal),
                required="NOT_APPLICABLE",
                operator=ComparisonOperator.absent,
                applicability="not_applicable",
            )
        )
    else:
        reqs.append(
            _req(
                "minimum_transfer_breadth",
                passed=snapshot.transfer_breadth_signal >= policy.minimum_transfer_breadth,
                current=_fmt(snapshot.transfer_breadth_signal),
                required=_fmt(policy.minimum_transfer_breadth),
                operator=ComparisonOperator.ge,
            )
        )

    # Retry observability + exclusive dependence cap.
    if policy.minimum_distinct_tasks_attempted is not None:
        reqs.append(
            _req(
                "minimum_distinct_tasks_attempted",
                passed=snapshot.distinct_tasks_attempted >= policy.minimum_distinct_tasks_attempted,
                current=str(snapshot.distinct_tasks_attempted),
                required=str(policy.minimum_distinct_tasks_attempted),
                operator=ComparisonOperator.ge,
            )
        )

    if policy.require_known_retry_dependence:
        known = snapshot.retry_dependence_signal is not None
        reqs.append(
            _req(
                "retry_dependence_observability",
                passed=known,
                current="None" if not known else _fmt(snapshot.retry_dependence_signal),
                required="known (not None)",
                operator=ComparisonOperator.is_not_none,
                applicability="required" if known else "unknown",
            )
        )
        if known and policy.exclusive_maximum_retry_dependence is not None:
            assert snapshot.retry_dependence_signal is not None
            reqs.append(
                _req(
                    "exclusive_maximum_retry_dependence",
                    passed=snapshot.retry_dependence_signal < policy.exclusive_maximum_retry_dependence,
                    current=_fmt(snapshot.retry_dependence_signal),
                    required=f"< {_fmt(policy.exclusive_maximum_retry_dependence)}",
                    operator=ComparisonOperator.lt,
                )
            )
        elif not known:
            # Unknown blocks D→A; record failed exclusive bound as unknown-blocked.
            reqs.append(
                _req(
                    "exclusive_maximum_retry_dependence",
                    passed=False,
                    current="None",
                    required=f"< {_fmt(policy.exclusive_maximum_retry_dependence)}",
                    operator=ComparisonOperator.lt,
                    applicability="unknown",
                )
            )
    else:
        # F→D: UNKNOWN retry allowed; known high dependence is advisory only via blockers.
        reqs.append(
            _req(
                "retry_dependence_observability",
                passed=True,
                current="None" if snapshot.retry_dependence_signal is None else _fmt(snapshot.retry_dependence_signal),
                required="UNKNOWN_OK",
                operator=ComparisonOperator.absent,
                applicability="not_applicable",
            )
        )

    # Blocker kinds.
    present = {b.kind for b in snapshot.blockers}
    for kind in sorted(policy.hard_blocker_kinds, key=lambda k: k.value):
        hit = kind in present
        reqs.append(
            _req(
                f"blocker_absent:{kind.value}",
                passed=not hit,
                current="present" if hit else "absent",
                required="absent",
                operator=ComparisonOperator.ne,
            )
        )

    for kind in sorted(policy.advisory_blocker_kinds, key=lambda k: k.value):
        hit = kind in present
        reqs.append(
            _req(
                f"advisory_blocker:{kind.value}",
                passed=True,  # advisory never hard-fails
                current="present" if hit else "absent",
                required="advisory",
                operator=ComparisonOperator.absent,
                applicability="advisory",
            )
        )

    # Future unknown blocking severities from S15.
    for b in snapshot.blockers:
        if b.kind in policy.hard_blocker_kinds or b.kind in policy.advisory_blocker_kinds:
            continue
        if b.severity == "blocking":
            reqs.append(
                _req(
                    f"blocker_absent:{b.kind.value}",
                    passed=False,
                    current="present",
                    required="absent",
                    operator=ComparisonOperator.ne,
                )
            )
        else:
            reqs.append(
                _req(
                    f"advisory_blocker:{b.kind.value}",
                    passed=True,
                    current="present",
                    required="advisory",
                    operator=ComparisonOperator.absent,
                    applicability="advisory",
                )
            )

    return reqs


def evaluate_speaking_transition_gate(
    snapshot: SpeakingStageSignalSnapshot,
) -> SpeakingStageTransitionDecision:
    """Authorize foundation→developing or developing→advanced within current CEFR."""
    current = SpeakingLearningStage(int(snapshot.current_stage))

    if current is SpeakingLearningStage.advanced:
        draft = SpeakingStageTransitionDecision(
            schema_version=TRANSITION_GATE_SCHEMA_VERSION,
            policy_version=TRANSITION_POLICY_VERSION,
            official_cefr=snapshot.official_cefr,
            current_stage=current,
            target_stage=None,
            decision=SpeakingStageTransitionDecisionKind.stay,
            authorized=False,
            signal_fingerprint=snapshot.snapshot_fingerprint,
            requirements=(),
            blocking_reasons=(),
            advisory_reasons=("already_at_advanced_within_cefr",),
            satisfied_requirements=(),
            unknown_requirements=(),
            decision_fingerprint="",
        )
        return replace(draft, decision_fingerprint=compute_decision_fingerprint(draft))

    target = SpeakingLearningStage(int(current) + 1)
    policy = policy_for_transition(current, target, official_cefr=snapshot.official_cefr)
    if policy is None:
        draft = SpeakingStageTransitionDecision(
            schema_version=TRANSITION_GATE_SCHEMA_VERSION,
            policy_version=TRANSITION_POLICY_VERSION,
            official_cefr=snapshot.official_cefr,
            current_stage=current,
            target_stage=None,
            decision=SpeakingStageTransitionDecisionKind.stay,
            authorized=False,
            signal_fingerprint=snapshot.snapshot_fingerprint,
            requirements=(),
            blocking_reasons=("no_policy_for_transition",),
            advisory_reasons=(),
            satisfied_requirements=(),
            unknown_requirements=(),
            decision_fingerprint="",
        )
        return replace(draft, decision_fingerprint=compute_decision_fingerprint(draft))

    requirements = tuple(_evaluate_policy(snapshot, policy))
    blocking = tuple(r.code for r in requirements if r.applicability == "required" and not r.passed)
    unknown = tuple(r.code for r in requirements if r.applicability == "unknown")
    # Unknown required observability also blocks.
    for r in requirements:
        if r.applicability == "unknown" and not r.passed and r.code not in blocking:
            blocking = blocking + (r.code,)
    advisory = tuple(
        r.code
        for r in requirements
        if r.applicability == "advisory" and r.current == "present"
    )
    # Support dependence always unknown — advisory info, never blocks.
    if any(b.kind is SpeakingStageBlockerKind.support_dependence_unknown for b in snapshot.blockers):
        if "advisory_blocker:support_dependence_unknown" not in advisory:
            advisory = advisory + ("advisory_blocker:support_dependence_unknown",)

    satisfied = tuple(r.code for r in requirements if r.passed and r.applicability == "required")
    authorized = len(blocking) == 0

    draft = SpeakingStageTransitionDecision(
        schema_version=TRANSITION_GATE_SCHEMA_VERSION,
        policy_version=policy.policy_version,
        official_cefr=snapshot.official_cefr,
        current_stage=current,
        target_stage=target,
        decision=(
            SpeakingStageTransitionDecisionKind.advance
            if authorized
            else SpeakingStageTransitionDecisionKind.stay
        ),
        authorized=authorized,
        signal_fingerprint=snapshot.snapshot_fingerprint,
        requirements=requirements,
        blocking_reasons=blocking,
        advisory_reasons=advisory,
        satisfied_requirements=satisfied,
        unknown_requirements=unknown,
        decision_fingerprint="",
    )
    return replace(draft, decision_fingerprint=compute_decision_fingerprint(draft))
