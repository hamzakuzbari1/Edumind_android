"""Deterministic mastery update engine for Speaking Knowledge Model (S2)."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_curriculum.types import (
    SPEAKING_SKILL_GRAPH_VERSION,
    SpeakingSkillNode,
)
from app.services.language_speaking_knowledge_model.observation_validation import (
    evidence_coverage_for_state,
    validate_observation,
)
from app.services.language_speaking_knowledge_model.types import (
    MasteryRequirementEvaluation,
    MistakePatternSummary,
    OBSERVATION_HISTORY_CAP,
    OBSERVATION_INDEX_CAP,
    ObservationApplyResult,
    SkillObservationRecord,
    SpeakingSkillEvidenceObservation,
    SpeakingSkillStatus,
    StudentSpeakingKnowledgeModel,
    StudentSpeakingSkillState,
)

# Documented constants — see KNOWLEDGE_MODEL_ARCHITECTURE.md
EMA_BASE_ALPHA = 0.18
INCIDENTAL_WEIGHT = 0.32
STABILITY_VARIANCE_WEIGHT = 0.45
STABILITY_CONSECUTIVE_WEIGHT = 0.25
STABILITY_CONTEXT_WEIGHT = 0.20
STABILITY_MISTAKE_WEIGHT = 0.10
MASTERED_STABILITY_FLOOR = 0.62
STABLE_STABILITY_FLOOR = 0.48
DEVELOPING_MASTERY_FLOOR = 0.22
OBSERVED_EVIDENCE_MIN = 1
DEMONSTRATED_MASTERY_FLOOR = 0.35
DEMONSTRATED_STABILITY_FLOOR = 0.40
AT_RISK_RETENTION_THRESHOLD = 0.62
REVISION_IMPROVEMENT_MIN_DELTA = 0.08


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _days_between(later: datetime, earlier: datetime) -> float:
    return max(0.0, (later - earlier).total_seconds() / 86400.0)


def evaluate_mastery_requirements(
    node: SpeakingSkillNode,
    state: StudentSpeakingSkillState,
) -> MasteryRequirementEvaluation:
    req = node.mastery_requirements
    reasons: list[str] = []

    if state.evidence_count < req.minimum_evidence_count:
        reasons.append(f"evidence_count {state.evidence_count} < {req.minimum_evidence_count}")

    coverage = evidence_coverage_for_state(node, state.observed_dimensions)
    if coverage.coverage_ratio < 1.0:
        reasons.append(f"missing dimensions: {list(coverage.missing_dimensions)}")

    if req.pronunciation_threshold is not None and state.mastery < req.pronunciation_threshold:
        reasons.append(f"mastery {state.mastery:.3f} < pronunciation {req.pronunciation_threshold}")

    if req.communicative_success_threshold is not None:
        if state.recent_performance < req.communicative_success_threshold:
            reasons.append(
                f"recent_performance {state.recent_performance:.3f} "
                f"< {req.communicative_success_threshold}"
            )

    if req.response_relevance_threshold is not None and state.mastery < req.response_relevance_threshold:
        reasons.append("response relevance not demonstrated")

    if req.distinct_word_contexts is not None and state.distinct_context_count < req.distinct_word_contexts:
        reasons.append(
            f"contexts {state.distinct_context_count} < {req.distinct_word_contexts}"
        )

    if req.minimum_interaction_turns is not None and state.evidence_count < req.minimum_interaction_turns:
        reasons.append(
            f"interaction turns {state.evidence_count} < {req.minimum_interaction_turns}"
        )

    if req.repeated_successful_contexts is not None:
        if state.successful_evidence_count < req.repeated_successful_contexts:
            reasons.append(
                f"successful contexts {state.successful_evidence_count} "
                f"< {req.repeated_successful_contexts}"
            )

    stability_floor = min(0.85, 0.45 + 0.08 * req.stability_sessions)
    if state.stability < stability_floor:
        reasons.append(f"stability {state.stability:.3f} < {stability_floor:.3f}")

    for flag_name in (
        "task_response_required",
        "organization_required",
        "fluency_required",
        "grammar_vocabulary_required",
    ):
        if getattr(req, flag_name) and coverage.coverage_ratio < 1.0:
            reasons.append(f"{flag_name} evidence incomplete")

    return MasteryRequirementEvaluation(met=not reasons, reasons=tuple(reasons))


def _compute_variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def _update_stability(
    state: StudentSpeakingSkillState,
    *,
    performance: float,
    success: bool,
    new_context: bool,
    mistake_penalty: float,
) -> float:
    recent = [r.performance for r in state.observation_history[-6:]] + [performance]
    variance = _compute_variance(recent)
    variance_component = _clamp01(1.0 - min(1.0, variance * 4.0))

    consecutive_component = _clamp01(min(1.0, state.consecutive_successes / 5.0))
    if not success:
        consecutive_component *= 0.5

    context_component = _clamp01(min(1.0, state.distinct_context_count / 4.0))
    if not new_context:
        context_component *= 0.85

    mistake_component = _clamp01(1.0 - mistake_penalty)

    blended = (
        STABILITY_VARIANCE_WEIGHT * variance_component
        + STABILITY_CONSECUTIVE_WEIGHT * consecutive_component
        + STABILITY_CONTEXT_WEIGHT * context_component
        + STABILITY_MISTAKE_WEIGHT * mistake_component
    )
    if state.evidence_count <= 1:
        return 0.0
    return _clamp01(0.65 * state.stability + 0.35 * blended)


def _update_confidence(state: StudentSpeakingSkillState, *, obs_confidence: float, contradictory: bool) -> float:
    if state.evidence_count <= 0:
        return 0.0
    evidence_factor = 1.0 - math.exp(-0.35 * state.evidence_count * max(0.1, obs_confidence))
    base = _clamp01(evidence_factor * max(state.mastery, state.recent_performance))
    if contradictory:
        base *= 0.82
    return _clamp01(0.7 * state.confidence + 0.3 * base)


def _compute_retention_risk(
    node: SpeakingSkillNode,
    state: StudentSpeakingSkillState,
    *,
    now: datetime,
) -> float:
    if state.evidence_count == 0 or state.current_status == SpeakingSkillStatus.unseen:
        return 0.0
    if state.peak_mastery < DEMONSTRATED_MASTERY_FLOOR and state.peak_stability < DEMONSTRATED_STABILITY_FLOOR:
        return 0.0

    if not state.last_practiced_at:
        return 0.0

    last = _parse_iso(state.last_practiced_at)
    days_idle = _days_between(now, last)

    srs = node.spaced_repetition_profile
    interval = float(srs.initial_interval_days if srs else 7)
    max_interval = float(srs.max_interval_days if srs else 90)
    idle_ratio = _clamp01(days_idle / max(interval, 1.0))

    decay = _clamp01(idle_ratio * (1.0 - state.stability * 0.5))
    trend_penalty = 0.0
    if len(state.observation_history) >= 2:
        last_two = state.observation_history[-2:]
        if last_two[1].performance < last_two[0].performance - 0.15:
            trend_penalty = 0.15

    return _clamp01(decay * 0.7 + (1.0 - state.recent_performance) * 0.2 + trend_penalty)


def _derive_status(
    state: StudentSpeakingSkillState,
    *,
    requirements_met: bool,
) -> SpeakingSkillStatus:
    if state.evidence_count == 0:
        return SpeakingSkillStatus.unseen

    if requirements_met:
        return SpeakingSkillStatus.mastered

    if (
        state.retention_risk >= AT_RISK_RETENTION_THRESHOLD
        and state.peak_mastery >= DEMONSTRATED_MASTERY_FLOOR
        and state.peak_stability >= DEMONSTRATED_STABILITY_FLOOR
    ):
        return SpeakingSkillStatus.at_risk

    if state.stability >= STABLE_STABILITY_FLOOR and state.mastery >= DEVELOPING_MASTERY_FLOOR:
        return SpeakingSkillStatus.stable

    if state.mastery >= DEVELOPING_MASTERY_FLOOR or state.evidence_count >= 3:
        return SpeakingSkillStatus.developing

    if state.evidence_count >= OBSERVED_EVIDENCE_MIN:
        return SpeakingSkillStatus.observed

    return SpeakingSkillStatus.unseen


def _append_history(state: StudentSpeakingSkillState, record: SkillObservationRecord) -> None:
    state.observation_history.append(record)
    if len(state.observation_history) > OBSERVATION_HISTORY_CAP:
        state.observation_history = state.observation_history[-OBSERVATION_HISTORY_CAP:]


def _update_mistake_patterns(
    model: StudentSpeakingKnowledgeModel,
    *,
    tags: tuple[str, ...],
    context_id: str,
    observed_at: str,
) -> float:
    penalty = 0.0
    for tag in tags:
        if not tag.strip():
            continue
        summary = model.mistake_patterns.get(tag)
        if summary is None:
            summary = MistakePatternSummary(
                mistake_tag=tag,
                occurrence_count=0,
                recent_occurrence_count=0,
                last_seen_at=None,
                affected_contexts=[],
            )
        summary.occurrence_count += 1
        summary.recent_occurrence_count = min(10, summary.recent_occurrence_count + 1)
        summary.last_seen_at = observed_at
        if context_id and context_id not in summary.affected_contexts:
            summary.affected_contexts.append(context_id)
            if len(summary.affected_contexts) > 8:
                summary.affected_contexts = summary.affected_contexts[-8:]
        model.mistake_patterns[tag] = summary
        penalty += 0.08
    return min(0.5, penalty)


def apply_observation(
    model: StudentSpeakingKnowledgeModel,
    observation: SpeakingSkillEvidenceObservation,
    *,
    now: datetime,
) -> ObservationApplyResult:
    if observation.observation_id in model.applied_observation_ids:
        existing_skill = model.applied_observation_ids[observation.observation_id]
        state = model.skill_states.get(existing_skill)
        return ObservationApplyResult(
            applied=False,
            idempotent=True,
            skill_id=observation.skill_id,
            reason="duplicate observation_id",
            state=state,
        )

    node, err = validate_observation(observation, now=now)
    if err is not None:
        return ObservationApplyResult(applied=False, skill_id=observation.skill_id, reason=err.message)

    assert node is not None
    state = model.skill_states.get(observation.skill_id)
    if state is None:
        state = StudentSpeakingSkillState(skill_id=observation.skill_id)
        model.skill_states[observation.skill_id] = state

    weight = observation.confidence * (1.0 if observation.target_skill else INCIDENTAL_WEIGHT)
    alpha = EMA_BASE_ALPHA * weight

    prev_performance = state.recent_performance
    contradictory = (
        state.evidence_count > 0
        and abs(observation.performance - prev_performance) > 0.45
        and observation.confidence >= 0.5
    )

    state.mastery = _clamp01(state.mastery + alpha * (observation.performance - state.mastery))
    state.recent_performance = _clamp01(
        (1.0 - alpha) * state.recent_performance + alpha * observation.performance
        if state.evidence_count > 0
        else observation.performance
    )
    state.confidence = _update_confidence(
        state, obs_confidence=observation.confidence, contradictory=contradictory
    )

    state.evidence_count += 1
    if observation.success:
        state.successful_evidence_count += 1
        state.consecutive_successes += 1
        state.consecutive_failures = 0
    else:
        state.consecutive_failures += 1
        state.consecutive_successes = 0

    new_context = observation.context_id not in state.context_fingerprints
    if new_context:
        state.context_fingerprints.append(observation.context_id)
        state.distinct_context_count += 1

    for dim in observation.evidence_dimensions:
        state.observed_dimensions[dim] = state.observed_dimensions.get(dim, 0) + 1

    revision_delta = 0.0
    if observation.previous_observation_id and observation.revision_number > 0:
        for rec in reversed(state.observation_history):
            if rec.observation_id == observation.previous_observation_id:
                revision_delta = observation.performance - rec.performance
                break
        if revision_delta >= REVISION_IMPROVEMENT_MIN_DELTA:
            state.revision_improvement = _clamp01(revision_delta)
        elif revision_delta > 0:
            state.revision_improvement = _clamp01(revision_delta * 0.5)

    mistake_penalty = _update_mistake_patterns(
        model,
        tags=observation.mistake_tags,
        context_id=observation.context_id,
        observed_at=observation.observed_at,
    )
    for tag in observation.mistake_tags:
        if tag:
            state.mistake_tag_counts[tag] = state.mistake_tag_counts.get(tag, 0) + 1
            state.recent_mistake_tags.append(tag)
            if len(state.recent_mistake_tags) > 12:
                state.recent_mistake_tags = state.recent_mistake_tags[-12:]
    state.mistake_recurrence = _clamp01(
        min(1.0, sum(state.mistake_tag_counts.values()) / max(1, state.evidence_count))
    )

    state.stability = _update_stability(
        state,
        performance=observation.performance,
        success=observation.success,
        new_context=new_context,
        mistake_penalty=mistake_penalty,
    )

    state.peak_mastery = max(state.peak_mastery, state.mastery)
    state.peak_stability = max(state.peak_stability, state.stability)

    _append_history(
        state,
        SkillObservationRecord(
            observation_id=observation.observation_id,
            observed_at=observation.observed_at,
            performance=observation.performance,
            confidence=observation.confidence,
            context_id=observation.context_id,
            success=observation.success,
            revision_number=observation.revision_number,
            mistake_tags=list(observation.mistake_tags),
        ),
    )

    state.last_practiced_at = observation.observed_at
    state.last_updated_at = observation.observed_at
    if state.first_observed_at is None:
        state.first_observed_at = observation.observed_at

    req_eval = evaluate_mastery_requirements(node, state)
    state.meets_mastery_requirements = req_eval.met
    state.retention_risk = _compute_retention_risk(node, state, now=now)
    state.current_status = _derive_status(state, requirements_met=req_eval.met)

    model.applied_observation_ids[observation.observation_id] = observation.skill_id
    if len(model.applied_observation_ids) > OBSERVATION_INDEX_CAP:
        excess = len(model.applied_observation_ids) - OBSERVATION_INDEX_CAP
        for key in list(model.applied_observation_ids.keys())[:excess]:
            del model.applied_observation_ids[key]

    model.total_observations += 1
    model.last_updated_at = observation.observed_at
    if not model.graph_version:
        model.graph_version = SPEAKING_SKILL_GRAPH_VERSION

    return ObservationApplyResult(
        applied=True,
        skill_id=observation.skill_id,
        state=state,
    )


def apply_observations_batch(
    model: StudentSpeakingKnowledgeModel,
    observations: list[SpeakingSkillEvidenceObservation],
    *,
    now: datetime,
) -> list[ObservationApplyResult]:
    """Apply observations in order; roll back all changes on first hard failure."""
    from app.services.language_speaking_knowledge_model.storage import (
        knowledge_model_from_dict,
        knowledge_model_to_dict,
    )

    snapshot = knowledge_model_to_dict(model)
    results: list[ObservationApplyResult] = []

    for obs in observations:
        result = apply_observation(model, obs, now=now)
        results.append(result)
        if not result.applied and not result.idempotent:
            restored = knowledge_model_from_dict(
                snapshot,
                student_id=model.student_id,
                language_id=model.language_id,
            )
            model.skill_states = restored.skill_states
            model.deprecated_skill_states = restored.deprecated_skill_states
            model.mistake_patterns = restored.mistake_patterns
            model.applied_observation_ids = restored.applied_observation_ids
            model.total_observations = restored.total_observations
            model.last_updated_at = restored.last_updated_at
            model.compatibility_notes = restored.compatibility_notes
            model.graph_version = restored.graph_version
            break
    return results


def refresh_retention_for_model(
    model: StudentSpeakingKnowledgeModel,
    *,
    now: datetime,
) -> None:
    """Recompute retention risk and status at a given time (deterministic tests)."""
    for skill_id, state in model.skill_states.items():
        node = SPEAKING_SKILL_GRAPH.node_by_id(skill_id)
        if node is None:
            continue
        req_eval = evaluate_mastery_requirements(node, state)
        state.meets_mastery_requirements = req_eval.met
        state.retention_risk = _compute_retention_risk(node, state, now=now)
        state.current_status = _derive_status(state, requirements_met=req_eval.met)
