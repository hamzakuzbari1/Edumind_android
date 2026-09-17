"""Candidate skill evidence bridge from S5/S6 + task targets (S7).

Emits S2-compatible observation fields without calling apply_observation or mutating S2.
"""

from __future__ import annotations

from app.services.language_speaking_educational_analyzer.types import SpeakingEducationalFacts
from app.services.language_speaking_evaluator.evaluation_result import SpeakingCandidateSkillEvidence
from app.services.language_speaking_evaluator.input_types import SpeakingEvaluationContext, SpeakingEvaluationInput
from app.services.language_speaking_evaluator.rule_facts_types import SpeakingRuleEvaluationFacts


def build_candidate_skill_evidence(
    *,
    rule: SpeakingRuleEvaluationFacts,
    input: SpeakingEvaluationInput,
    context: SpeakingEvaluationContext,
    educational: SpeakingEducationalFacts | None,
) -> tuple[SpeakingCandidateSkillEvidence, ...]:
    """Populate skill evidence from S5/S6 candidate_skill_ids and task target skills."""
    target_ids = set(context.task.target_skill_ids)
    context_id = context.evaluation_id
    evidence_ids = input.evidence_reference_ids
    out: dict[str, SpeakingCandidateSkillEvidence] = {}

    def _upsert(
        skill_id: str,
        *,
        source_dimension: str,
        performance: float,
        confidence: float,
        evidence_dimensions: tuple[str, ...],
        success: bool,
        mistake_tags: tuple[str, ...] = (),
        reason: str = "",
    ) -> None:
        if not skill_id:
            return
        existing = out.get(skill_id)
        if existing is not None and existing.performance <= performance:
            return
        out[skill_id] = SpeakingCandidateSkillEvidence(
            skill_id=skill_id,
            source_dimension=source_dimension,
            performance=performance,
            confidence=confidence,
            evidence_dimensions=evidence_dimensions,
            context_id=context_id,
            success=success,
            mistake_tags=mistake_tags,
            target_skill=skill_id in target_ids,
            communicative_impact=performance if source_dimension == "task_response" else None,
            supporting_evidence_ids=evidence_ids,
            reason=reason,
        )

    for sid in rule.pronunciation.affected_candidate_skill_ids:
        _upsert(
            sid,
            source_dimension="pronunciation",
            performance=max(0.0, 1.0 - rule.pronunciation.substitution_count * 0.05),
            confidence=rule.pronunciation.reliability,
            evidence_dimensions=("phoneme_alignment", "pronunciation_confidence"),
            success=rule.pronunciation_dimension.passed,
            mistake_tags=rule.pronunciation.issue_tags,
            reason="S5 pronunciation issue mapping.",
        )

    for sid in rule.prosody.affected_candidate_skill_ids:
        _upsert(
            sid,
            source_dimension="fluency_delivery",
            performance=rule.fluency_delivery.score,
            confidence=rule.prosody.reliability,
            evidence_dimensions=("pauses", "speaking_rate", "rhythm"),
            success=rule.fluency_delivery.passed,
            mistake_tags=rule.prosody.issue_tags,
            reason="S6 prosody/delivery issue mapping.",
        )

    if educational and educational.available:
        task_score = educational.task_response.score
        for sid in target_ids:
            _upsert(
                sid,
                source_dimension="task_response",
                performance=task_score,
                confidence=0.65,
                evidence_dimensions=("semantic_task_response", "meaning_success"),
                success=task_score >= 0.55,
                reason="Task target skill from educational task-response read.",
            )

    return tuple(out.values())
