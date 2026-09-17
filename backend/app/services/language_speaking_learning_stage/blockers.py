"""Deterministic stage blockers (S15). Never invented by AI."""

from __future__ import annotations

from app.services.language_speaking_learning_stage.aggregation import (
    AT_RISK_SHARE_BLOCK_THRESHOLD,
    RETENTION_SHARE_BLOCK_THRESHOLD,
    RETRY_DEPENDENCE_BLOCK_THRESHOLD,
    STABILITY_LOW_THRESHOLD,
)
from app.services.language_speaking_learning_stage.types import (
    DataSufficiencyVerdict,
    SpeakingStageBlocker,
    SpeakingStageBlockerKind,
)


def derive_stage_blockers(
    *,
    data_sufficiency: DataSufficiencyVerdict,
    coverage_ratio: float,
    core_skill_coverage_ratio: float,
    core_skill_count: int,
    performance_stability_signal: float,
    retry_dependence_signal: float | None,
    retention_risk_signal: float,
    transfer_breadth_signal: float,
    at_risk_skill_ratio: float,
    stable_skill_ratio: float,
    in_level_mastery_avg: float,
) -> tuple[SpeakingStageBlocker, ...]:
    blockers: list[SpeakingStageBlocker] = []

    # Informational: support applied evidence is unavailable in S15.
    blockers.append(
        SpeakingStageBlocker(
            kind=SpeakingStageBlockerKind.support_dependence_unknown,
            severity="info",
            student_safe_message=(
                "We don't yet track which support you used during practice. "
                "Stage decisions ignore fabricated support dependence."
            ),
        )
    )

    if data_sufficiency is DataSufficiencyVerdict.insufficient:
        blockers.append(
            SpeakingStageBlocker(
                kind=SpeakingStageBlockerKind.insufficient_evidence,
                severity="blocking",
                student_safe_message=(
                    "You need more speaking practice evidence before moving forward "
                    "within your current level."
                ),
            )
        )

    if coverage_ratio < 0.25:
        blockers.append(
            SpeakingStageBlocker(
                kind=SpeakingStageBlockerKind.low_curriculum_coverage,
                severity="blocking",
                student_safe_message=(
                    "You've only practiced a small part of this level's speaking skills so far."
                ),
            )
        )

    if core_skill_count > 0 and core_skill_coverage_ratio < 0.5:
        blockers.append(
            SpeakingStageBlocker(
                kind=SpeakingStageBlockerKind.core_skill_gap,
                severity="blocking",
                student_safe_message=(
                    "Some foundational skills for this level still need practice evidence."
                ),
            )
        )

    if (
        data_sufficiency is not DataSufficiencyVerdict.insufficient
        and performance_stability_signal < STABILITY_LOW_THRESHOLD
        and in_level_mastery_avg > 0
    ):
        blockers.append(
            SpeakingStageBlocker(
                kind=SpeakingStageBlockerKind.unstable_performance,
                severity="warning",
                student_safe_message=(
                    "Your recent speaking performance still varies a lot. Keep practicing for consistency."
                ),
            )
        )

    if retry_dependence_signal is not None and retry_dependence_signal >= RETRY_DEPENDENCE_BLOCK_THRESHOLD:
        blockers.append(
            SpeakingStageBlocker(
                kind=SpeakingStageBlockerKind.repeated_retry_dependence,
                severity="warning",
                student_safe_message=(
                    "You've needed several retries on recent tasks. Aim for successful completion "
                    "with fewer attempts."
                ),
            )
        )

    if retention_risk_signal >= RETENTION_SHARE_BLOCK_THRESHOLD:
        blockers.append(
            SpeakingStageBlocker(
                kind=SpeakingStageBlockerKind.high_retention_risk,
                severity="warning",
                student_safe_message=(
                    "Some skills you practiced earlier may be getting rusty. A short review will help."
                ),
            )
        )

    # Transfer blocker only when the student already has enough coverage to expect transfer work.
    if (
        data_sufficiency is DataSufficiencyVerdict.sufficient
        and stable_skill_ratio >= 0.2
        and transfer_breadth_signal < 0.25
    ):
        blockers.append(
            SpeakingStageBlocker(
                kind=SpeakingStageBlockerKind.insufficient_transfer_evidence,
                severity="warning",
                student_safe_message=(
                    "Try using the same skills in a new situation so they transfer beyond one context."
                ),
            )
        )

    if at_risk_skill_ratio >= AT_RISK_SHARE_BLOCK_THRESHOLD:
        blockers.append(
            SpeakingStageBlocker(
                kind=SpeakingStageBlockerKind.too_many_at_risk_skills,
                severity="blocking",
                student_safe_message=(
                    "Several skills from this level are at risk. Strengthen them before moving up."
                ),
            )
        )

    return tuple(blockers)
