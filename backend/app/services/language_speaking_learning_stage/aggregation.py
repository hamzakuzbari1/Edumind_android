"""Deterministic stage-signal dimension calculators (S15).

Pure functions over in-level S1 nodes + S2 skill states + optional S11 lineage.
No AI. No mutation.
"""

from __future__ import annotations

import math
from statistics import mean

from app.services.language_speaking_curriculum.types import SpeakingSkillNode
from app.services.language_speaking_knowledge_model.types import (
    SpeakingSkillStatus,
    StudentSpeakingKnowledgeModel,
    StudentSpeakingSkillState,
)
from app.services.language_speaking_learning_stage.curriculum_scope import core_curriculum_skills
from app.services.language_speaking_learning_stage.types import DataSufficiencyVerdict
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    SpeakingAttemptStatus,
    SpeakingSessionAttemptLineage,
)

# Align with S12 / engine floors where applicable.
RETENTION_RISK_THRESHOLD = 0.62
TRANSFER_MASTERY_THRESHOLD = 0.60
RECENT_HISTORY_WINDOW = 6
RETRY_DEPENDENCE_BLOCK_THRESHOLD = 0.55
AT_RISK_SHARE_BLOCK_THRESHOLD = 0.35
RETENTION_SHARE_BLOCK_THRESHOLD = 0.35
COVERAGE_PARTIAL_RATIO = 0.25
COVERAGE_SUFFICIENT_RATIO = 0.40
MIN_EVIDENCED_PARTIAL = 3
MIN_EVIDENCED_SUFFICIENT = 5
MIN_TOTAL_OBSERVATIONS = 8
MIN_DISTINCT_TASKS = 2
MIN_CORE_WITH_EVIDENCE = 2
STABILITY_LOW_THRESHOLD = 0.40
TRANSFER_WELL_LEARNED_MIN_EVIDENCE = 2


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _state_for(
    model: StudentSpeakingKnowledgeModel | None,
    skill_id: str,
) -> StudentSpeakingSkillState | None:
    if model is None:
        return None
    return model.skill_states.get(skill_id)


def _evidenced(state: StudentSpeakingSkillState | None) -> bool:
    return state is not None and state.evidence_count > 0


def _well_learned(state: StudentSpeakingSkillState) -> bool:
    return (
        state.mastery >= TRANSFER_MASTERY_THRESHOLD
        or state.current_status in (SpeakingSkillStatus.stable, SpeakingSkillStatus.mastered)
    ) and state.evidence_count >= TRANSFER_WELL_LEARNED_MIN_EVIDENCE


def coverage_metrics(
    nodes: tuple[SpeakingSkillNode, ...],
    model: StudentSpeakingKnowledgeModel | None,
) -> dict[str, float | int]:
    curriculum_count = len(nodes)
    if curriculum_count == 0:
        return {
            "curriculum_skill_count": 0,
            "skills_with_evidence_count": 0,
            "coverage_ratio": 0.0,
            "core_skill_coverage_ratio": 0.0,
            "sufficient_evidence_ratio": 0.0,
            "core_skill_count": 0,
            "core_skills_with_min_evidence": 0,
        }

    evidenced = 0
    sufficient = 0
    for node in nodes:
        st = _state_for(model, node.skill_id)
        if not _evidenced(st):
            continue
        evidenced += 1
        min_req = max(1, int(node.mastery_requirements.minimum_evidence_count))
        if st is not None and st.evidence_count >= min_req:
            sufficient += 1

    core = core_curriculum_skills(nodes)
    core_count = len(core)
    core_evidenced = 0
    for node in core:
        st = _state_for(model, node.skill_id)
        min_req = max(1, int(node.mastery_requirements.minimum_evidence_count))
        if st is not None and st.evidence_count >= min_req:
            core_evidenced += 1

    return {
        "curriculum_skill_count": curriculum_count,
        "skills_with_evidence_count": evidenced,
        "coverage_ratio": evidenced / curriculum_count,
        "core_skill_coverage_ratio": (core_evidenced / core_count) if core_count else 0.0,
        "sufficient_evidence_ratio": sufficient / curriculum_count,
        "core_skill_count": core_count,
        "core_skills_with_min_evidence": core_evidenced,
    }


def status_ratios(
    nodes: tuple[SpeakingSkillNode, ...],
    model: StudentSpeakingKnowledgeModel | None,
) -> dict[str, float]:
    """Ratios over FULL in-level curriculum (unseen skills count as non-stable)."""
    n = len(nodes)
    if n == 0:
        return {
            "stable_skill_ratio": 0.0,
            "developing_skill_ratio": 0.0,
            "at_risk_skill_ratio": 0.0,
            "in_level_mastery_avg": 0.0,
            "in_level_stability_avg": 0.0,
        }

    stable = 0
    developing = 0
    at_risk = 0
    mastery_vals: list[float] = []
    stability_vals: list[float] = []

    for node in nodes:
        st = _state_for(model, node.skill_id)
        if not _evidenced(st) or st is None:
            continue
        if st.current_status in (SpeakingSkillStatus.stable, SpeakingSkillStatus.mastered):
            stable += 1
        elif st.current_status in (SpeakingSkillStatus.developing, SpeakingSkillStatus.observed):
            developing += 1
        elif st.current_status is SpeakingSkillStatus.at_risk:
            at_risk += 1
        mastery_vals.append(st.mastery)
        stability_vals.append(st.stability)

    return {
        "stable_skill_ratio": stable / n,
        "developing_skill_ratio": developing / n,
        "at_risk_skill_ratio": at_risk / n,
        "in_level_mastery_avg": mean(mastery_vals) if mastery_vals else 0.0,
        "in_level_stability_avg": mean(stability_vals) if stability_vals else 0.0,
    }


def recency_stability_signals(
    nodes: tuple[SpeakingSkillNode, ...],
    model: StudentSpeakingKnowledgeModel | None,
) -> dict[str, float]:
    """Recent success/failure + performance stability from per-skill history windows."""
    successes = 0
    failures = 0
    total = 0
    per_skill_stability: list[float] = []

    for node in nodes:
        st = _state_for(model, node.skill_id)
        if not _evidenced(st) or st is None:
            continue
        hist = list(st.observation_history[-RECENT_HISTORY_WINDOW:])
        if not hist:
            # Lifetime counters as weak fallback for skills without history records.
            if st.successful_evidence_count:
                successes += st.successful_evidence_count
                total += st.evidence_count
                failures += max(0, st.evidence_count - st.successful_evidence_count)
            per_skill_stability.append(st.stability)
            continue
        for rec in hist:
            total += 1
            if rec.success:
                successes += 1
            else:
                failures += 1
        perfs = [r.performance for r in hist]
        if len(perfs) < 2:
            per_skill_stability.append(st.stability)
        else:
            m = mean(perfs)
            var = sum((p - m) ** 2 for p in perfs) / len(perfs)
            per_skill_stability.append(_clamp01(1.0 - var * 4.0))

    if total <= 0:
        return {
            "recent_success_signal": 0.0,
            "recent_failure_signal": 0.0,
            "performance_stability_signal": 0.0,
        }
    return {
        "recent_success_signal": successes / total,
        "recent_failure_signal": failures / total,
        "performance_stability_signal": mean(per_skill_stability) if per_skill_stability else 0.0,
    }


def transfer_and_retention_signals(
    nodes: tuple[SpeakingSkillNode, ...],
    model: StudentSpeakingKnowledgeModel | None,
) -> dict[str, float]:
    well: list[StudentSpeakingSkillState] = []
    evidenced: list[StudentSpeakingSkillState] = []
    for node in nodes:
        st = _state_for(model, node.skill_id)
        if not _evidenced(st) or st is None:
            continue
        evidenced.append(st)
        if _well_learned(st):
            well.append(st)

    if not evidenced:
        return {
            "transfer_breadth_signal": 0.0,
            "retention_risk_signal": 0.0,
            "context_diversity_signal": 0.0,
        }

    transferred = sum(1 for st in well if st.distinct_context_count >= 2)
    transfer_breadth = (transferred / len(well)) if well else 0.0

    at_riskish = sum(
        1
        for st in evidenced
        if st.retention_risk >= RETENTION_RISK_THRESHOLD
        or st.current_status is SpeakingSkillStatus.at_risk
    )
    retention_risk_signal = at_riskish / len(evidenced)

    contexts = [float(st.distinct_context_count) for st in evidenced]
    # Normalize roughly: 0 contexts → 0, 2+ → ~1.
    diversity = mean([_clamp01(c / 2.0) for c in contexts]) if contexts else 0.0

    return {
        "transfer_breadth_signal": transfer_breadth,
        "retention_risk_signal": retention_risk_signal,
        "context_diversity_signal": diversity,
    }


def retry_dependence_from_lineage(
    lineage: SpeakingSessionAttemptLineage | None,
) -> tuple[float | None, int]:
    """S11-derived retry dependence. Returns (signal|None, distinct_tasks_attempted).

    Signal ~ mean over tasks of (attempt_number_of_latest - 1) / max(1, attempts_for_task - abandoneds?).
    Higher ⇒ more retry dependence. None when no task attempts exist.
    """
    if lineage is None or not lineage.attempts:
        return None, 0

    by_task: dict[str, list] = {}
    for att in lineage.attempts:
        by_task.setdefault(att.task_id, []).append(att)

    scores: list[float] = []
    for task_id, attempts in by_task.items():
        # Prefer retry-chain depth via retry_of / attempt_number.
        max_num = max(a.attempt_number for a in attempts)
        failed = sum(1 for a in attempts if a.status is SpeakingAttemptStatus.failed)
        # Dependence grows with retry attempts beyond the first.
        dependence = _clamp01((max_num - 1) / max(3.0, float(max_num)))
        if failed >= 2:
            dependence = _clamp01(dependence + 0.15)
        scores.append(dependence)

    if not scores:
        return None, 0
    return mean(scores), len(by_task)


def evaluate_data_sufficiency(
    *,
    curriculum_skill_count: int,
    skills_with_evidence_count: int,
    coverage_ratio: float,
    total_observations: int,
    distinct_tasks_attempted: int,
    core_skills_with_min_evidence: int,
) -> DataSufficiencyVerdict:
    if curriculum_skill_count <= 0:
        return DataSufficiencyVerdict.insufficient

    partial_min = max(MIN_EVIDENCED_PARTIAL, math.ceil(COVERAGE_PARTIAL_RATIO * curriculum_skill_count))
    sufficient_min = max(
        MIN_EVIDENCED_SUFFICIENT, math.ceil(COVERAGE_SUFFICIENT_RATIO * curriculum_skill_count)
    )

    if skills_with_evidence_count < partial_min or coverage_ratio < COVERAGE_PARTIAL_RATIO:
        return DataSufficiencyVerdict.insufficient

    if (
        skills_with_evidence_count >= sufficient_min
        and coverage_ratio >= COVERAGE_SUFFICIENT_RATIO
        and total_observations >= MIN_TOTAL_OBSERVATIONS
        and distinct_tasks_attempted >= MIN_DISTINCT_TASKS
        and core_skills_with_min_evidence >= MIN_CORE_WITH_EVIDENCE
    ):
        return DataSufficiencyVerdict.sufficient

    return DataSufficiencyVerdict.partial
