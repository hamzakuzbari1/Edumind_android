"""Gather SpeakingStageSignalSnapshot from authoritative state (S15).

Pure projection. Rebuild on demand. Never writes learning_stage_speaking,
official_speaking_cefr, promotion readiness, or S2 mastery.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.language_speaking.enums import SpeakingLearningStage
from app.services.language_speaking_knowledge_model.engine import refresh_retention_for_model
from app.services.language_speaking_knowledge_model.types import StudentSpeakingKnowledgeModel
from app.services.language_speaking_learning_stage.aggregation import (
    coverage_metrics,
    evaluate_data_sufficiency,
    recency_stability_signals,
    retry_dependence_from_lineage,
    status_ratios,
    transfer_and_retention_signals,
)
from app.services.language_speaking_learning_stage.blockers import derive_stage_blockers
from app.services.language_speaking_learning_stage.curriculum_scope import (
    curriculum_skills_for_official_cefr,
)
from app.services.language_speaking_learning_stage.fingerprint import compute_snapshot_fingerprint
from app.services.language_speaking_learning_stage.types import (
    STAGE_SIGNAL_SCHEMA_VERSION,
    SUPPORT_DEPENDENCE_UNKNOWN,
    SpeakingStageSignalSnapshot,
)
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    AmbiguousActiveAttemptError,
    SpeakingSessionAttemptLineage,
    assert_active_attempt_integrity,
)


def gather_speaking_stage_signals(
    *,
    official_cefr: str,
    current_stage: SpeakingLearningStage | int,
    knowledge_model: StudentSpeakingKnowledgeModel | None,
    attempt_lineage: SpeakingSessionAttemptLineage | None = None,
    now: datetime | None = None,
    refresh_retention: bool = True,
) -> SpeakingStageSignalSnapshot:
    """Build a deterministic stage-signal snapshot (projection only).

    Raises ``AmbiguousActiveAttemptError`` (from S11) if lineage is malformed —
    S15 must not aggregate over ambiguous execution state.
    """
    if attempt_lineage is not None:
        assert_active_attempt_integrity(attempt_lineage)

    stage = SpeakingLearningStage(max(1, min(3, int(current_stage))))
    cefr = (official_cefr or "A2").upper()
    nodes = curriculum_skills_for_official_cefr(cefr)

    # Retention is time-dependent — refresh at read time when a model is present.
    if knowledge_model is not None and refresh_retention:
        refresh_retention_for_model(knowledge_model, now=now or datetime.now(tz=timezone.utc))

    cov = coverage_metrics(nodes, knowledge_model)
    status = status_ratios(nodes, knowledge_model)
    recent = recency_stability_signals(nodes, knowledge_model)
    xfer = transfer_and_retention_signals(nodes, knowledge_model)
    retry_signal, distinct_tasks = retry_dependence_from_lineage(attempt_lineage)

    total_obs = int(knowledge_model.total_observations) if knowledge_model is not None else 0
    sufficiency = evaluate_data_sufficiency(
        curriculum_skill_count=int(cov["curriculum_skill_count"]),
        skills_with_evidence_count=int(cov["skills_with_evidence_count"]),
        coverage_ratio=float(cov["coverage_ratio"]),
        total_observations=total_obs,
        distinct_tasks_attempted=distinct_tasks,
        core_skills_with_min_evidence=int(cov["core_skills_with_min_evidence"]),
    )

    blockers = derive_stage_blockers(
        data_sufficiency=sufficiency,
        coverage_ratio=float(cov["coverage_ratio"]),
        core_skill_coverage_ratio=float(cov["core_skill_coverage_ratio"]),
        core_skill_count=int(cov["core_skill_count"]),
        performance_stability_signal=float(recent["performance_stability_signal"]),
        retry_dependence_signal=retry_signal,
        retention_risk_signal=float(xfer["retention_risk_signal"]),
        transfer_breadth_signal=float(xfer["transfer_breadth_signal"]),
        at_risk_skill_ratio=float(status["at_risk_skill_ratio"]),
        stable_skill_ratio=float(status["stable_skill_ratio"]),
        in_level_mastery_avg=float(status["in_level_mastery_avg"]),
    )

    # Fingerprint computed after assembly with a placeholder, then reassigned
    # (frozen dataclass → rebuild with fingerprint).
    draft = SpeakingStageSignalSnapshot(
        schema_version=STAGE_SIGNAL_SCHEMA_VERSION,
        official_cefr=cefr,
        current_stage=stage,
        curriculum_skill_count=int(cov["curriculum_skill_count"]),
        skills_with_evidence_count=int(cov["skills_with_evidence_count"]),
        coverage_ratio=float(cov["coverage_ratio"]),
        core_skill_coverage_ratio=float(cov["core_skill_coverage_ratio"]),
        sufficient_evidence_ratio=float(cov["sufficient_evidence_ratio"]),
        stable_skill_ratio=float(status["stable_skill_ratio"]),
        developing_skill_ratio=float(status["developing_skill_ratio"]),
        at_risk_skill_ratio=float(status["at_risk_skill_ratio"]),
        in_level_mastery_avg=float(status["in_level_mastery_avg"]),
        in_level_stability_avg=float(status["in_level_stability_avg"]),
        recent_success_signal=float(recent["recent_success_signal"]),
        recent_failure_signal=float(recent["recent_failure_signal"]),
        retry_dependence_signal=retry_signal,
        support_dependence_signal=SUPPORT_DEPENDENCE_UNKNOWN,
        retention_risk_signal=float(xfer["retention_risk_signal"]),
        transfer_breadth_signal=float(xfer["transfer_breadth_signal"]),
        context_diversity_signal=float(xfer["context_diversity_signal"]),
        performance_stability_signal=float(recent["performance_stability_signal"]),
        data_sufficiency=sufficiency,
        blockers=blockers,
        snapshot_fingerprint="",
        total_observations=total_obs,
        distinct_tasks_attempted=distinct_tasks,
        core_skills_with_min_evidence=int(cov["core_skills_with_min_evidence"]),
        core_skill_count=int(cov["core_skill_count"]),
    )
    fp = compute_snapshot_fingerprint(draft)
    return SpeakingStageSignalSnapshot(
        schema_version=draft.schema_version,
        official_cefr=draft.official_cefr,
        current_stage=draft.current_stage,
        curriculum_skill_count=draft.curriculum_skill_count,
        skills_with_evidence_count=draft.skills_with_evidence_count,
        coverage_ratio=draft.coverage_ratio,
        core_skill_coverage_ratio=draft.core_skill_coverage_ratio,
        sufficient_evidence_ratio=draft.sufficient_evidence_ratio,
        stable_skill_ratio=draft.stable_skill_ratio,
        developing_skill_ratio=draft.developing_skill_ratio,
        at_risk_skill_ratio=draft.at_risk_skill_ratio,
        in_level_mastery_avg=draft.in_level_mastery_avg,
        in_level_stability_avg=draft.in_level_stability_avg,
        recent_success_signal=draft.recent_success_signal,
        recent_failure_signal=draft.recent_failure_signal,
        retry_dependence_signal=draft.retry_dependence_signal,
        support_dependence_signal=draft.support_dependence_signal,
        retention_risk_signal=draft.retention_risk_signal,
        transfer_breadth_signal=draft.transfer_breadth_signal,
        context_diversity_signal=draft.context_diversity_signal,
        performance_stability_signal=draft.performance_stability_signal,
        data_sufficiency=draft.data_sufficiency,
        blockers=draft.blockers,
        snapshot_fingerprint=fp,
        total_observations=draft.total_observations,
        distinct_tasks_attempted=draft.distinct_tasks_attempted,
        core_skills_with_min_evidence=draft.core_skills_with_min_evidence,
        core_skill_count=draft.core_skill_count,
    )


# Re-export for clarity at the gather boundary.
__all__ = ["gather_speaking_stage_signals", "AmbiguousActiveAttemptError"]
