"""S8 — canonical S7 evaluation evidence → S2 knowledge model mutation bridge.

Reuses ``candidate_skill_evidence`` from ``SpeakingEvaluationEngineResult`` only.
No second evaluator, no CEFR/stage/promotion writes.

Context ID rule: ``context_id = turn_reference`` (live turn id), not the ephemeral
``evaluation_id``. Same-turn retry reuses the same context; distinct turns get
distinct context ids.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_evaluator.evaluation_result import (
    SpeakingEvaluationEngineResult,
)
from app.services.language_speaking_evaluation_runtime.knowledge_bridge_types import (
    LANGUAGE_SPEAKING_KNOWLEDGE_BRIDGE_VERSION,
    SkippedCandidateEvidence,
    SpeakingKnowledgeMutationBridgeResult,
    SpeakingKnowledgeMutationStatus,
)
from app.services.language_speaking_knowledge_model.engine import apply_observations_batch
from app.services.language_speaking_knowledge_model.json_mutation import mutate_speaking_knowledge_model
from app.services.language_speaking_knowledge_model.types import (
    ObservationSourceType,
    SpeakingSkillEvidenceObservation,
)


def _mint_observation_id(
    *,
    student_id: int,
    session_id: str,
    turn_reference: str,
    engine_version: str,
    skill_id: str,
    source_dimension: str,
) -> str:
    raw = f"{student_id}:{session_id}:{turn_reference}:{engine_version}:{skill_id}:{source_dimension}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:20]
    return f"obs-{digest}"


def _dimension_overlap_sufficient(skill_id: str, evidence_dimensions: tuple[str, ...]) -> bool:
    node = SPEAKING_SKILL_GRAPH.node_by_id(skill_id)
    if node is None:
        return False
    required = set(node.evidence_requirements.evidence_codes)
    observed = set(evidence_dimensions)
    overlap = required & observed
    return len(overlap) >= node.evidence_requirements.minimum_dimensions


def build_speaking_skill_observations(
    evaluation: SpeakingEvaluationEngineResult,
    *,
    turn_reference: str,
    session_id: str,
    observed_at: str | None = None,
    revision_number: int = 0,
    source_type: ObservationSourceType = ObservationSourceType.evaluation_turn,
) -> SpeakingKnowledgeMutationBridgeResult:
    """Translate S7 candidate evidence into S2 observations (pure, no DB)."""
    ts = observed_at or evaluation.evaluated_at
    unknown: list[str] = []
    unavailable: list[SkippedCandidateEvidence] = []
    skipped: list[SkippedCandidateEvidence] = []
    observations: list[SpeakingSkillEvidenceObservation] = []

    # S19 quarantine: promotion_assessment evidence is labeled but not mastery-applied.
    if source_type == ObservationSourceType.promotion_assessment:
        return SpeakingKnowledgeMutationBridgeResult(
            bridge_version=LANGUAGE_SPEAKING_KNOWLEDGE_BRIDGE_VERSION,
            source_evaluation_version=evaluation.engine_version,
            turn_reference=turn_reference,
            observations=(),
            skipped_candidate_evidence=tuple(
                SkippedCandidateEvidence(
                    skill_id=c.skill_id,
                    source_dimension=c.source_dimension,
                    reason="quarantined_promotion_assessment",
                )
                for c in evaluation.candidate_skill_evidence
            ),
            mutation_status=SpeakingKnowledgeMutationStatus.quarantined_promotion_assessment,
            mutation_error_code="quarantined_promotion_assessment",
        )

    for candidate in evaluation.candidate_skill_evidence:
        node = SPEAKING_SKILL_GRAPH.node_by_id(candidate.skill_id)
        if node is None:
            if candidate.skill_id not in unknown:
                unknown.append(candidate.skill_id)
            skipped.append(
                SkippedCandidateEvidence(
                    skill_id=candidate.skill_id,
                    source_dimension=candidate.source_dimension,
                    reason="unknown_skill_id",
                )
            )
            continue

        if not candidate.evidence_dimensions:
            unavailable.append(
                SkippedCandidateEvidence(
                    skill_id=candidate.skill_id,
                    source_dimension=candidate.source_dimension,
                    reason="empty_evidence_dimensions",
                )
            )
            continue

        if not _dimension_overlap_sufficient(candidate.skill_id, candidate.evidence_dimensions):
            unavailable.append(
                SkippedCandidateEvidence(
                    skill_id=candidate.skill_id,
                    source_dimension=candidate.source_dimension,
                    reason="insufficient_dimension_overlap",
                )
            )
            continue

        obs_id = _mint_observation_id(
            student_id=evaluation.student_id,
            session_id=session_id,
            turn_reference=turn_reference,
            engine_version=evaluation.engine_version,
            skill_id=candidate.skill_id,
            source_dimension=candidate.source_dimension,
        )
        observations.append(
            SpeakingSkillEvidenceObservation(
                observation_id=obs_id,
                skill_id=candidate.skill_id,
                observed_at=ts,
                performance=candidate.performance,
                confidence=candidate.confidence,
                evidence_dimensions=candidate.evidence_dimensions,
                context_id=turn_reference,
                success=candidate.success,
                target_skill=candidate.target_skill,
                session_id=session_id,
                mistake_tags=candidate.mistake_tags,
                revision_number=revision_number,
                previous_observation_id=None,
                communicative_impact=candidate.communicative_impact,
                source_type=source_type,
            )
        )

    if not evaluation.candidate_skill_evidence:
        status = SpeakingKnowledgeMutationStatus.no_observations
    elif observations:
        status = SpeakingKnowledgeMutationStatus.no_observations  # resolved after apply
    elif unavailable or unknown:
        status = SpeakingKnowledgeMutationStatus.skipped_all
    else:
        status = SpeakingKnowledgeMutationStatus.no_observations

    return SpeakingKnowledgeMutationBridgeResult(
        bridge_version=LANGUAGE_SPEAKING_KNOWLEDGE_BRIDGE_VERSION,
        source_evaluation_version=evaluation.engine_version,
        turn_reference=turn_reference,
        observations=tuple(observations),
        skipped_candidate_evidence=tuple(skipped),
        unknown_skill_ids=tuple(unknown),
        unavailable_dimensions=tuple(unavailable),
        mutation_status=status,
    )


async def apply_speaking_evaluation_to_knowledge_model(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    evaluation: SpeakingEvaluationEngineResult | None,
    turn_reference: str,
    session_id: str,
    now: datetime | None = None,
    source_type: ObservationSourceType = ObservationSourceType.evaluation_turn,
) -> SpeakingKnowledgeMutationBridgeResult:
    """Apply S7 evaluation facts to S2 via atomic JSONB mutation."""
    if evaluation is None:
        return SpeakingKnowledgeMutationBridgeResult(
            bridge_version=LANGUAGE_SPEAKING_KNOWLEDGE_BRIDGE_VERSION,
            source_evaluation_version="",
            turn_reference=turn_reference,
            mutation_status=SpeakingKnowledgeMutationStatus.s7_unavailable,
            mutation_error_code="s7_unavailable",
        )

    # S19: never mutate S2 mastery from SPA evidence (quarantine).
    if source_type == ObservationSourceType.promotion_assessment:
        return SpeakingKnowledgeMutationBridgeResult(
            bridge_version=LANGUAGE_SPEAKING_KNOWLEDGE_BRIDGE_VERSION,
            source_evaluation_version=evaluation.engine_version,
            turn_reference=turn_reference,
            mutation_status=SpeakingKnowledgeMutationStatus.quarantined_promotion_assessment,
            mutation_error_code="quarantined_promotion_assessment",
        )

    ts = now or datetime.now(tz=timezone.utc)
    built = build_speaking_skill_observations(
        evaluation,
        turn_reference=turn_reference,
        session_id=session_id,
        observed_at=evaluation.evaluated_at,
        revision_number=evaluation.revision_number,
        source_type=source_type,
    )

    if not built.observations:
        status = (
            SpeakingKnowledgeMutationStatus.skipped_all
            if evaluation.candidate_skill_evidence
            else SpeakingKnowledgeMutationStatus.no_observations
        )
        return SpeakingKnowledgeMutationBridgeResult(
            bridge_version=built.bridge_version,
            source_evaluation_version=built.source_evaluation_version,
            turn_reference=turn_reference,
            observations=(),
            skipped_candidate_evidence=built.skipped_candidate_evidence,
            unknown_skill_ids=built.unknown_skill_ids,
            unavailable_dimensions=built.unavailable_dimensions,
            mutation_status=status,
        )

    try:

        def _mutator(model):
            return apply_observations_batch(model, list(built.observations), now=ts)

        _row, batch_results = await mutate_speaking_knowledge_model(
            db,
            student_id=student_id,
            language_id=language_id,
            mutator=_mutator,
        )
    except Exception as exc:
        return SpeakingKnowledgeMutationBridgeResult(
            bridge_version=built.bridge_version,
            source_evaluation_version=built.source_evaluation_version,
            turn_reference=turn_reference,
            observations=built.observations,
            skipped_candidate_evidence=built.skipped_candidate_evidence,
            unknown_skill_ids=built.unknown_skill_ids,
            unavailable_dimensions=built.unavailable_dimensions,
            mutation_status=SpeakingKnowledgeMutationStatus.mutation_failed,
            mutation_error_code=type(exc).__name__,
        )

    if batch_results is None:
        return SpeakingKnowledgeMutationBridgeResult(
            bridge_version=built.bridge_version,
            source_evaluation_version=built.source_evaluation_version,
            turn_reference=turn_reference,
            observations=built.observations,
            skipped_candidate_evidence=built.skipped_candidate_evidence,
            unknown_skill_ids=built.unknown_skill_ids,
            unavailable_dimensions=built.unavailable_dimensions,
            mutation_status=SpeakingKnowledgeMutationStatus.mutation_failed,
            mutation_error_code="progression_row_unavailable",
        )

    applied_ids: list[str] = []
    hard_failure = False
    for obs, result in zip(built.observations, batch_results, strict=False):
        if result.applied or result.idempotent:
            applied_ids.append(obs.observation_id)
        elif not result.idempotent:
            hard_failure = True
            break

    if hard_failure or not applied_ids:
        return SpeakingKnowledgeMutationBridgeResult(
            bridge_version=built.bridge_version,
            source_evaluation_version=built.source_evaluation_version,
            turn_reference=turn_reference,
            observations=built.observations,
            skipped_candidate_evidence=built.skipped_candidate_evidence,
            unknown_skill_ids=built.unknown_skill_ids,
            unavailable_dimensions=built.unavailable_dimensions,
            mutation_status=SpeakingKnowledgeMutationStatus.mutation_failed,
            mutation_error_code="batch_apply_failed",
        )

    return SpeakingKnowledgeMutationBridgeResult(
        bridge_version=built.bridge_version,
        source_evaluation_version=built.source_evaluation_version,
        turn_reference=turn_reference,
        observations=built.observations,
        applied_observation_ids=tuple(applied_ids),
        skipped_candidate_evidence=built.skipped_candidate_evidence,
        unknown_skill_ids=built.unknown_skill_ids,
        unavailable_dimensions=built.unavailable_dimensions,
        mutation_status=SpeakingKnowledgeMutationStatus.applied,
    )
