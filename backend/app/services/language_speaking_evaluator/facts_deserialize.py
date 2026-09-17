"""Reconstruct canonical speaking evaluation result from persistence dict."""

from __future__ import annotations

from app.services.language_speaking_educational_analyzer.types import (
    GrammarNote,
    SpeakingEducationalFacts,
    VocabularyInsight,
    DimensionInsight,
)
from app.services.language_speaking_evaluator.evaluation_result import SpeakingCandidateSkillEvidence
from app.services.language_speaking_evaluator.evaluation_facts_types import DimensionEvidenceStatus
from app.services.language_speaking_evaluator.evaluation_result import (
    CompletionEligibilityFacts,
    DimensionFacts,
    EvidenceSummaryFacts,
    ExplanationFacts,
    RevisionReadinessFacts,
    SpeakingEvaluationEngineResult,
)
from app.services.language_speaking_evaluator.input_types import (
    SpeakingGoalContext,
    SpeakingOfficialCefrContext,
    SpeakingTaskContext,
)


def _dim(raw: object, *, default_name: str = "") -> DimensionFacts:
    if not isinstance(raw, dict):
        return DimensionFacts(
            default_name,
            DimensionEvidenceStatus.insufficient_evidence,
            None,
            0.0,
            "",
            (),
            (),
            0.0,
            0.0,
            False,
        )
    status_raw = str(raw.get("status") or DimensionEvidenceStatus.partial.value)
    try:
        status = DimensionEvidenceStatus(status_raw)
    except ValueError:
        status = DimensionEvidenceStatus.partial
    norm = raw.get("normalized_value")
    return DimensionFacts(
        dimension=str(raw.get("dimension") or default_name),
        status=status,
        normalized_value=float(norm) if norm is not None else None,
        confidence=float(raw.get("confidence") or 0),
        reason=str(raw.get("reason") or ""),
        supporting_evidence_ids=tuple(raw.get("supporting_evidence_ids") or ()),
        limitations=tuple(raw.get("limitations") or ()),
        score=float(raw.get("score") or 0),
        weight=float(raw.get("weight") or 0),
        passed=bool(raw.get("passed")),
        evidence_codes=tuple(raw.get("evidence_codes") or ()),
        errors=tuple(raw.get("errors") or ()),
    )


def _edu_from_raw(raw: object) -> SpeakingEducationalFacts | None:
    if not isinstance(raw, dict) or not raw.get("available"):
        return None

    def _insight(key: str) -> DimensionInsight:
        block = raw.get(key) or {}
        if not isinstance(block, dict):
            return DimensionInsight(0.0, "")
        return DimensionInsight(score=float(block.get("score") or 0), reason=str(block.get("reason") or ""))

    vocab_raw = raw.get("spoken_vocabulary") or {}
    vocab = VocabularyInsight(0.0, "")
    if isinstance(vocab_raw, dict):
        vocab = VocabularyInsight(
            score=float(vocab_raw.get("score") or 0),
            reason=str(vocab_raw.get("reason") or ""),
            range_comment=str(vocab_raw.get("range_comment") or ""),
            repeated_words=tuple(vocab_raw.get("repeated_words") or ()),
            weak_choices=tuple(vocab_raw.get("weak_choices") or ()),
            missing_topic_words=tuple(vocab_raw.get("missing_topic_words") or ()),
            suggestions=tuple(vocab_raw.get("suggestions") or ()),
        )

    notes: list[GrammarNote] = []
    for item in raw.get("grammar_notes") or []:
        if isinstance(item, dict) and str(item.get("issue") or "").strip():
            notes.append(
                GrammarNote(
                    issue=str(item.get("issue") or ""),
                    rule=str(item.get("rule") or ""),
                    fix=str(item.get("fix") or ""),
                    example=str(item.get("example") or ""),
                )
            )

    return SpeakingEducationalFacts(
        task_response=_insight("task_response"),
        topic_understanding=_insight("topic_understanding"),
        idea_development=_insight("idea_development"),
        coherence=_insight("coherence"),
        spoken_grammar=_insight("spoken_grammar"),
        spoken_vocabulary=vocab,
        communicative_effectiveness=_insight("communicative_effectiveness"),
        interaction_quality=_insight("interaction_quality"),
        goal_alignment=_insight("goal_alignment"),
        observed_cefr_estimate=str(raw.get("observed_cefr_estimate") or ""),
        cefr_reason=str(raw.get("cefr_reason") or ""),
        major_learning_issue=str(raw.get("major_learning_issue") or ""),
        pronunciation_interpretation=str(raw.get("pronunciation_interpretation") or ""),
        delivery_interpretation=str(raw.get("delivery_interpretation") or ""),
        previous_attempt_comparison=str(raw.get("previous_attempt_comparison") or ""),
        learning_diagnosis=str(raw.get("learning_diagnosis") or ""),
        single_revision_priority=str(raw.get("single_revision_priority") or ""),
        encouragement=str(raw.get("encouragement") or ""),
        strengths=tuple(raw.get("strengths") or ()),
        grammar_notes=tuple(notes),
        available=True,
        analyzer_version=str(raw.get("analyzer_version") or ""),
        model_name=str(raw.get("model_name") or ""),
        source=str(raw.get("source") or "claude"),
    )


def evaluation_result_from_dict(raw: dict[str, object]) -> SpeakingEvaluationEngineResult | None:
    if not isinstance(raw, dict):
        return None

    dims = raw.get("dimensions") if isinstance(raw.get("dimensions"), dict) else raw
    task_ctx = raw.get("task_context") or {}
    goal_ctx = raw.get("goal_context") or {}
    cefr_ctx = raw.get("official_cefr_context") or {}
    ev_sum = raw.get("evidence_summary") or {}
    expl = raw.get("explanation") or {}
    rev = raw.get("revision_readiness") or {}
    comp = raw.get("completion_eligibility") or {}

    if not isinstance(task_ctx, dict):
        task_ctx = {}
    if not isinstance(goal_ctx, dict):
        goal_ctx = {}
    if not isinstance(cefr_ctx, dict):
        cefr_ctx = {}
    if not isinstance(ev_sum, dict):
        ev_sum = {}
    if not isinstance(expl, dict):
        expl = {}
    if not isinstance(rev, dict):
        rev = {}
    if not isinstance(comp, dict):
        comp = {}

    candidate_raw = raw.get("candidate_skill_evidence") or []
    candidates: list[SpeakingCandidateSkillEvidence] = []
    if isinstance(candidate_raw, list):
        for item in candidate_raw:
            if not isinstance(item, dict):
                continue
            candidates.append(
                SpeakingCandidateSkillEvidence(
                    skill_id=str(item.get("skill_id") or ""),
                    source_dimension=str(item.get("source_dimension") or ""),
                    performance=float(item.get("performance") or 0),
                    confidence=float(item.get("confidence") or 0),
                    evidence_dimensions=tuple(item.get("evidence_dimensions") or ()),
                    context_id=str(item.get("context_id") or ""),
                    success=bool(item.get("success")),
                    mistake_tags=tuple(item.get("mistake_tags") or ()),
                    target_skill=bool(item.get("target_skill")),
                    communicative_impact=float(item["communicative_impact"]) if item.get("communicative_impact") is not None else None,
                    supporting_evidence_ids=tuple(item.get("supporting_evidence_ids") or ()),
                    reason=str(item.get("reason") or ""),
                )
            )

    return SpeakingEvaluationEngineResult(
        evaluation_id=str(raw.get("evaluation_id") or ""),
        student_id=int(raw.get("student_id") or 0),
        language_id=int(raw.get("language_id") or 0),
        session_id=str(raw.get("session_id") or ""),
        task_id=str(raw.get("task_id") or ""),
        attempt_id=str(raw.get("attempt_id") or ""),
        revision_number=int(raw.get("revision_number") or 1),
        evaluated_at=str(raw.get("evaluated_at") or ""),
        task_context=SpeakingTaskContext(
            task_id=str(task_ctx.get("task_id") or ""),
            task_type=str(task_ctx.get("task_type") or ""),
            task_prompt=str(task_ctx.get("task_prompt") or ""),
            task_instructions=str(task_ctx.get("task_instructions") or ""),
            success_criteria=tuple(task_ctx.get("success_criteria") or ()),
            target_skill_ids=tuple(task_ctx.get("target_skill_ids") or ()),
        ),
        goal_context=SpeakingGoalContext(
            speaking_goal=str(goal_ctx.get("speaking_goal") or ""),
            goal_label=str(goal_ctx.get("goal_label") or ""),
        ),
        official_cefr_context=SpeakingOfficialCefrContext(
            official_cefr=str(cefr_ctx.get("official_cefr") or "B1"),
            band_descriptor=str(cefr_ctx.get("band_descriptor") or ""),
        ),
        evidence_summary=EvidenceSummaryFacts(
            availability={str(k): bool(v) for k, v in (ev_sum.get("availability") or {}).items()},
            reliability=float(ev_sum.get("reliability") or 0),
            provider_provenance=tuple(ev_sum.get("provider_provenance") or ()),
            evidence_reference_ids=tuple(ev_sum.get("evidence_reference_ids") or ()),
            processing_warnings=tuple(ev_sum.get("processing_warnings") or ()),
        ),
        task_response=_dim((dims or {}).get("task_response") if isinstance(dims, dict) else None, default_name="task_response"),
        topic_understanding=_dim((dims or {}).get("topic_understanding") if isinstance(dims, dict) else None, default_name="topic_understanding"),
        pronunciation=_dim((dims or {}).get("pronunciation") if isinstance(dims, dict) else None, default_name="pronunciation"),
        fluency_delivery=_dim((dims or {}).get("fluency_delivery") if isinstance(dims, dict) else None, default_name="fluency_delivery"),
        grammar=_dim((dims or {}).get("grammar") if isinstance(dims, dict) else None, default_name="grammar"),
        vocabulary=_dim((dims or {}).get("vocabulary") if isinstance(dims, dict) else None, default_name="vocabulary"),
        coherence=_dim((dims or {}).get("coherence") if isinstance(dims, dict) else None, default_name="coherence"),
        interaction=_dim((dims or {}).get("interaction") if isinstance(dims, dict) else None, default_name="interaction"),
        goal_alignment=_dim((dims or {}).get("goal_alignment") if isinstance(dims, dict) else None, default_name="goal_alignment"),
        cefr_validation=_dim((dims or {}).get("cefr_validation") if isinstance(dims, dict) else None, default_name="cefr_validation"),
        strengths=tuple(raw.get("strengths") or ()),
        weaknesses=tuple(raw.get("weaknesses") or ()),
        priority_issue=str(raw.get("priority_issue") or ""),
        revision_readiness=RevisionReadinessFacts(
            ready=bool(rev.get("ready")),
            blockers=tuple(rev.get("blockers") or ()),
        ),
        completion_eligibility=CompletionEligibilityFacts(
            eligible=bool(comp.get("eligible")),
            reason=str(comp.get("reason") or ""),
            semantic_task_met=bool(comp.get("semantic_task_met")),
            acoustic_only_boost_blocked=bool(comp.get("acoustic_only_boost_blocked")),
        ),
        comparison_with_previous_attempt=str(raw.get("comparison_with_previous_attempt") or ""),
        educational_analysis=_edu_from_raw(raw.get("educational_analysis")),
        candidate_skill_evidence=tuple(candidates),
        explanation=ExplanationFacts(
            summary=str(expl.get("summary") or ""),
            priority_issue=str(expl.get("priority_issue") or ""),
            improvements=tuple(expl.get("improvements") or ()),
            strengths=tuple(expl.get("strengths") or ()),
            focus_label=str(expl.get("focus_label") or ""),
        ),
        provider_provenance=tuple(raw.get("provider_provenance") or ()),
        weak_skills=tuple(raw.get("weak_skills") or ()),
        strong_skills=tuple(raw.get("strong_skills") or ()),
        overall_readiness=float(raw.get("overall_readiness") or 0),
        engine_version=str(raw.get("engine_version") or "7.0.0"),
    )
