"""Pure Grammar Mastery scoring engine (G2.2).

Deterministic, evidence-driven, idempotent. No LLM. No randomness.
"""

from __future__ import annotations

from app.services.language_grammar.enums import (
    GrammarEvidenceSourceSkill,
    GrammarMasteryState,
    GrammarObservationType,
    GrammarReinforcementSkill,
)
from app.services.language_grammar_catalog.types import GrammarCatalogSnapshot, GrammarTopic
from app.services.language_grammar_evidence.types import GrammarEvidenceObservation
from app.services.language_grammar_mastery.completion_gate import completion_gate_ready
from app.services.language_grammar_mastery.types import (
    APPLIED_OBSERVATION_INDEX_CAP,
    EMA_BASE_ALPHA,
    GrammarMasteryDimensions,
    GrammarMasteryRecord,
    GrammarMasterySnapshot,
    build_dimensions,
)


class GrammarMasteryError(ValueError):
    """Invalid mastery input or corrupted state."""


_OBS_WEIGHT: dict[GrammarObservationType, float] = {
    GrammarObservationType.formative: 0.7,
    GrammarObservationType.summative: 1.0,
    GrammarObservationType.transfer: 1.1,
    GrammarObservationType.retention: 1.0,
}


def _clamp100(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _ema(current: float, target: float, alpha: float) -> float:
    return _clamp100(current + alpha * (target - current))


def _accuracy_from_attempts(attempt_count: int, correct_count: int) -> float:
    if attempt_count <= 0:
        return 0.0
    return _clamp100(100.0 * (correct_count / attempt_count))


def _signals_from_observation(obs: GrammarEvidenceObservation) -> tuple[float, float, float, float]:
    accuracy = (
        obs.accuracy_signal
        if obs.accuracy_signal is not None
        else _accuracy_from_attempts(obs.attempt_count, obs.correct_count)
    )
    understanding = obs.understanding_signal if obs.understanding_signal is not None else accuracy
    if obs.fluency_signal is not None:
        fluency = obs.fluency_signal
    elif obs.source_skill in (
        GrammarEvidenceSourceSkill.speaking,
        GrammarEvidenceSourceSkill.listening,
    ):
        fluency = accuracy * 0.9
    else:
        fluency = accuracy * 0.75
    if obs.retention_signal is not None:
        retention = obs.retention_signal
    elif obs.observation_type is GrammarObservationType.retention:
        retention = accuracy
    else:
        retention = accuracy * 0.8
    return (_clamp100(understanding), _clamp100(accuracy), _clamp100(fluency), _clamp100(retention))


def _map_skill(
    source: GrammarEvidenceSourceSkill,
) -> GrammarReinforcementSkill | GrammarEvidenceSourceSkill:
    try:
        return GrammarReinforcementSkill(source.value)
    except ValueError:
        return source


def _derive_state(
    *,
    dimensions: GrammarMasteryDimensions,
    evidence_count: int,
    distinct_context_count: int,
    skill_coverage: frozenset,
    topic: GrammarTopic | None,
) -> GrammarMasteryState:
    if evidence_count <= 0:
        return GrammarMasteryState.unknown
    threshold = float(topic.mastery_threshold) if topic else 80.0
    req = topic.evidence_requirements if topic else None
    min_obs = req.min_observations if req else 3
    min_ctx = (
        max(topic.minimum_context_diversity, req.min_distinct_contexts)
        if topic and req
        else 2
    )
    min_skills = req.min_skills_covered if req else 1
    overall = dimensions.overall_mastery
    if (
        overall >= threshold
        and evidence_count >= min_obs
        and distinct_context_count >= min_ctx
        and len(skill_coverage) >= min_skills
    ):
        return GrammarMasteryState.mastered
    if overall >= 50.0 and evidence_count >= 2:
        return GrammarMasteryState.practicing
    return GrammarMasteryState.learning


def _empty_record(*, student_id: int, language_id: int, grammar_id: str) -> GrammarMasteryRecord:
    return GrammarMasteryRecord(
        student_id=student_id,
        language_id=language_id,
        grammar_id=grammar_id,
        state=GrammarMasteryState.unknown,
        dimensions=build_dimensions(understanding=0.0, accuracy=0.0, fluency=0.0, retention=0.0),
    )


def _replace_record(
    snapshot: GrammarMasterySnapshot,
    record: GrammarMasteryRecord,
    *,
    applied_observation_ids: frozenset[str] | None = None,
    contexts_by_grammar_id: dict[str, frozenset[str]] | None = None,
) -> GrammarMasterySnapshot:
    others = tuple(r for r in snapshot.records if r.grammar_id != record.grammar_id)
    return GrammarMasterySnapshot(
        student_id=snapshot.student_id,
        language_id=snapshot.language_id,
        records=tuple(sorted((*others, record), key=lambda r: r.grammar_id)),
        applied_observation_ids=(
            applied_observation_ids
            if applied_observation_ids is not None
            else snapshot.applied_observation_ids
        ),
        contexts_by_grammar_id=(
            contexts_by_grammar_id
            if contexts_by_grammar_id is not None
            else snapshot.contexts_by_grammar_id
        ),
        schema_version=snapshot.schema_version,
        enabled=snapshot.enabled,
    )


def apply_observation(
    snapshot: GrammarMasterySnapshot,
    obs: GrammarEvidenceObservation,
    *,
    catalog: GrammarCatalogSnapshot,
    known_contexts: set[str] | None = None,
) -> GrammarMasterySnapshot:
    """Apply one validated observation. Idempotent on observation_id."""
    if obs.observation_id in snapshot.applied_observation_ids:
        return snapshot

    topic = catalog.topic_by_id(obs.grammar_id)
    if topic is None:
        raise GrammarMasteryError(f"Unknown grammar_id: {obs.grammar_id}")

    record = snapshot.record_for(obs.grammar_id) or _empty_record(
        student_id=obs.student_id,
        language_id=obs.language_id,
        grammar_id=obs.grammar_id,
    )
    if record.student_id != obs.student_id or record.language_id != obs.language_id:
        raise GrammarMasteryError("Observation student/language mismatch")

    u_t, a_t, f_t, r_t = _signals_from_observation(obs)
    weight = _OBS_WEIGHT.get(obs.observation_type, 1.0)
    if obs.confidence is not None:
        weight *= max(0.3, min(1.0, float(obs.confidence)))
    alpha = min(0.35, EMA_BASE_ALPHA * weight)

    dims = record.dimensions
    new_dims = build_dimensions(
        understanding=_ema(dims.understanding, u_t, alpha),
        accuracy=_ema(dims.accuracy, a_t, alpha),
        fluency=_ema(dims.fluency, f_t, alpha),
        retention=_ema(dims.retention, r_t, alpha),
    )

    ctx_set = set(known_contexts or ()) | set(snapshot.contexts_by_grammar_id.get(obs.grammar_id) or ())
    ctx_set.add(obs.context)
    distinct_context_count = len(ctx_set)

    skill = _map_skill(obs.source_skill)
    coverage = frozenset(set(record.skill_coverage) | {skill})
    evidence_count = record.evidence_count + 1

    obs_conf = float(obs.confidence) if obs.confidence is not None else (0.55 + 0.05 * min(evidence_count, 8))
    confidence = _clamp100(
        (record.confidence * 0.7 + _clamp100(obs_conf * 100.0) * 0.3)
        if record.evidence_count
        else _clamp100(obs_conf * 100.0 if obs.confidence is not None else 50.0)
    )
    stability = _ema(record.stability, min(100.0, new_dims.overall_mastery), alpha * 0.5)
    retention_risk = _clamp100(100.0 - new_dims.retention)

    best_score_by_skill = dict(record.best_score_by_skill or {})
    skill_key = obs.source_skill.value
    obs_score = float(obs.score) if obs.score is not None else a_t
    best_score_by_skill[skill_key] = max(float(best_score_by_skill.get(skill_key) or 0.0), _clamp100(obs_score))

    best_attempt_count_by_skill = dict(record.best_attempt_count_by_skill or {})
    best_correct_count_by_skill = dict(record.best_correct_count_by_skill or {})
    best_attempt_count_by_skill[skill_key] = max(
        int(best_attempt_count_by_skill.get(skill_key) or 0),
        int(obs.attempt_count),
    )
    best_correct_count_by_skill[skill_key] = max(
        int(best_correct_count_by_skill.get(skill_key) or 0),
        int(obs.correct_count),
    )

    derived_state = _derive_state(
        dimensions=new_dims,
        evidence_count=evidence_count,
        distinct_context_count=distinct_context_count,
        skill_coverage=coverage,
        topic=topic,
    )
    gate_probe = GrammarMasteryRecord(
        student_id=record.student_id,
        language_id=record.language_id,
        grammar_id=record.grammar_id,
        state=derived_state,
        dimensions=new_dims,
        confidence=confidence,
        stability=stability,
        retention_risk=retention_risk,
        evidence_count=evidence_count,
        distinct_context_count=distinct_context_count,
        skill_coverage=coverage,
        best_score_by_skill=best_score_by_skill,
        best_attempt_count_by_skill=best_attempt_count_by_skill,
        best_correct_count_by_skill=best_correct_count_by_skill,
        introduced_at=record.introduced_at or obs.observed_at,
        last_seen_at=obs.observed_at or record.last_seen_at,
        last_updated_at=obs.observed_at or record.last_updated_at,
        last_mastered_at=record.last_mastered_at,
    )
    gate_ready = completion_gate_ready(gate_probe)
    state = GrammarMasteryState.mastered if gate_ready else (
        GrammarMasteryState.practicing if derived_state is GrammarMasteryState.mastered else derived_state
    )

    prev_state = record.state
    last_mastered = record.last_mastered_at
    if state is GrammarMasteryState.mastered and prev_state is not GrammarMasteryState.mastered:
        last_mastered = obs.observed_at or record.last_updated_at

    updated = GrammarMasteryRecord(
        student_id=record.student_id,
        language_id=record.language_id,
        grammar_id=record.grammar_id,
        state=state,
        dimensions=new_dims,
        confidence=confidence,
        stability=stability,
        retention_risk=retention_risk,
        evidence_count=evidence_count,
        distinct_context_count=distinct_context_count,
        skill_coverage=coverage,
        best_score_by_skill=best_score_by_skill,
        best_attempt_count_by_skill=best_attempt_count_by_skill,
        best_correct_count_by_skill=best_correct_count_by_skill,
        introduced_at=record.introduced_at or obs.observed_at,
        last_seen_at=obs.observed_at or record.last_seen_at,
        last_updated_at=obs.observed_at or record.last_updated_at,
        last_mastered_at=last_mastered,
    )

    applied = set(snapshot.applied_observation_ids)
    applied.add(obs.observation_id)
    if len(applied) > APPLIED_OBSERVATION_INDEX_CAP:
        applied = set(sorted(applied)[-APPLIED_OBSERVATION_INDEX_CAP:])

    contexts = dict(snapshot.contexts_by_grammar_id)
    contexts[obs.grammar_id] = frozenset(ctx_set)

    return _replace_record(
        snapshot,
        updated,
        applied_observation_ids=frozenset(applied),
        contexts_by_grammar_id=contexts,
    )


def apply_observations(
    snapshot: GrammarMasterySnapshot,
    observations: tuple[GrammarEvidenceObservation, ...],
    *,
    catalog: GrammarCatalogSnapshot,
) -> GrammarMasterySnapshot:
    """Apply observations in deterministic order (observed_at, observation_id)."""
    ordered = tuple(sorted(observations, key=lambda o: (o.observed_at or "", o.observation_id)))
    out = snapshot
    for obs in ordered:
        known = set(out.contexts_by_grammar_id.get(obs.grammar_id) or ())
        out = apply_observation(out, obs, catalog=catalog, known_contexts=known)
    return GrammarMasterySnapshot(
        student_id=out.student_id,
        language_id=out.language_id,
        records=out.records,
        applied_observation_ids=out.applied_observation_ids,
        contexts_by_grammar_id=out.contexts_by_grammar_id,
        schema_version=out.schema_version,
        enabled=True,
    )


def empty_snapshot(*, student_id: int, language_id: int) -> GrammarMasterySnapshot:
    return GrammarMasterySnapshot(student_id=student_id, language_id=language_id)


def disabled_mastery_snapshot(*, student_id: int, language_id: int) -> GrammarMasterySnapshot:
    return GrammarMasterySnapshot(
        student_id=student_id,
        language_id=language_id,
        enabled=False,
    )
