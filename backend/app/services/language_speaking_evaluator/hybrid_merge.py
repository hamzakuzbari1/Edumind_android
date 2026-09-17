"""Merge rule facts + Claude educational facts → canonical SpeakingEvaluationEngineResult."""

from __future__ import annotations

from dataclasses import replace

from app.services.language_speaking_educational_analyzer.types import SpeakingEducationalFacts
from app.services.language_speaking_evaluator.candidate_skill_evidence import build_candidate_skill_evidence
from app.services.language_speaking_evaluator.evaluation_facts_types import DimensionEvidenceStatus
from app.services.language_speaking_evaluator.evaluation_result import (
    SPEAKING_EVALUATION_RESULT_VERSION,
    CompletionEligibilityFacts,
    DimensionFacts,
    ExplanationFacts,
    RevisionReadinessFacts,
    SpeakingEvaluationEngineResult,
)
from app.services.language_speaking_evaluator.input_types import SpeakingEvaluationContext, SpeakingEvaluationInput
from app.services.language_speaking_evaluator.rule_facts_types import SpeakingRuleEvaluationFacts

HYBRID_ENGINE_VERSION = SPEAKING_EVALUATION_RESULT_VERSION

_EMOTIONAL_INFERENCE_MARKERS = (
    "nervous",
    "anxious",
    "bored",
    "unconfident",
    "confident",
    "happy",
    "sad",
    "angry",
    "frustrated",
    "embarrassed",
)


def _merge_dimension(
    rule_dim: DimensionFacts,
    *,
    edu_score: float | None,
    edu_reason: str,
    min_confidence: float = 0.35,
) -> DimensionFacts:
    if edu_score is None or not edu_reason:
        return rule_dim
    blended = (rule_dim.score * 0.35) + (edu_score * 0.65)
    status = (
        DimensionEvidenceStatus.met
        if blended >= 0.65
        else DimensionEvidenceStatus.partial
        if blended >= 0.4
        else DimensionEvidenceStatus.not_met
    )
    passed = status in {DimensionEvidenceStatus.met, DimensionEvidenceStatus.partial} and blended >= 0.55
    return replace(
        rule_dim,
        status=status,
        score=blended,
        normalized_value=edu_score,
        confidence=max(rule_dim.confidence, min_confidence),
        reason=edu_reason or rule_dim.reason,
        passed=passed and not rule_dim.errors,
    )


def _sanitize_acoustic_interpretation(
    text: str,
    *,
    allowed_issue_tags: tuple[str, ...],
    dimension: str,
) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    lower = cleaned.lower()
    if any(marker in lower for marker in _EMOTIONAL_INFERENCE_MARKERS):
        return f"{dimension}: emotional inference removed — cite evidence tags only."
    if allowed_issue_tags:
        if not any(tag.split(":")[-1].replace("_", " ") in lower or tag in lower for tag in allowed_issue_tags):
            return f"{dimension}: LLM claim not traceable to evidence tags {', '.join(allowed_issue_tags[:3])}."
    return cleaned


def _merge_explanation(
    rule: SpeakingRuleEvaluationFacts,
    educational: SpeakingEducationalFacts | None,
) -> ExplanationFacts:
    expl = rule.explanation
    if educational is None or not educational.available:
        return expl

    improvements: list[str] = list(expl.improvements)

    def _add(line: str) -> None:
        line = (line or "").strip()
        if line and line not in improvements:
            improvements.append(line)

    for note in educational.grammar_notes[:3]:
        line = note.fix or note.issue
        if line:
            _add(line)
    if educational.task_response.score < 0.6 and educational.task_response.reason:
        _add(educational.task_response.reason)
    if educational.spoken_vocabulary.suggestions:
        for s in educational.spoken_vocabulary.suggestions[:2]:
            _add(s)
    if educational.single_revision_priority:
        _add(educational.single_revision_priority)

    priority = expl.priority_issue
    if educational.learning_diagnosis:
        priority = educational.learning_diagnosis
    elif educational.major_learning_issue:
        priority = educational.major_learning_issue

    summary = expl.summary
    if educational.learning_diagnosis:
        summary = f"{expl.summary} Teacher analysis: {educational.learning_diagnosis}".strip()

    strengths = list(expl.strengths)
    for s in educational.strengths:
        if s and s not in strengths:
            strengths.append(s)
    if educational.encouragement and educational.encouragement not in strengths:
        strengths.append(educational.encouragement)

    focus = educational.major_learning_issue or expl.focus_label
    return ExplanationFacts(
        summary=summary,
        priority_issue=priority,
        improvements=tuple(dict.fromkeys(improvements))[:8],
        strengths=tuple(dict.fromkeys(strengths))[:5],
        focus_label=focus,
    )


def merge_speaking_evaluation(
    rule: SpeakingRuleEvaluationFacts,
    educational: SpeakingEducationalFacts | None,
    *,
    input: SpeakingEvaluationInput,
    context: SpeakingEvaluationContext,
) -> SpeakingEvaluationEngineResult:
    """Canonical merge — acoustic gates from rules; LLM enriches semantics only."""
    edu = educational if educational and educational.available else None

    task_dim = rule.task_response
    topic_dim = rule.topic_understanding
    grammar_dim = rule.grammar
    vocab_dim = rule.vocabulary
    coherence_dim = rule.coherence
    goal_dim = rule.goal_alignment
    interaction_dim = rule.interaction
    cefr_dim = rule.cefr_validation

    semantic_task_met = rule.transcript.task_keyword_overlap_ratio >= 0.35 and not rule.transcript.is_empty_response

    if edu is not None:
        task_dim = _merge_dimension(rule.task_response, edu_score=edu.task_response.score, edu_reason=edu.task_response.reason)
        topic_dim = _merge_dimension(rule.topic_understanding, edu_score=edu.topic_understanding.score, edu_reason=edu.topic_understanding.reason)
        grammar_dim = _merge_dimension(rule.grammar, edu_score=edu.spoken_grammar.score, edu_reason=edu.spoken_grammar.reason)
        vocab_dim = _merge_dimension(
            rule.vocabulary,
            edu_score=edu.spoken_vocabulary.score,
            edu_reason=edu.spoken_vocabulary.reason or edu.spoken_vocabulary.range_comment,
        )
        coherence_dim = _merge_dimension(rule.coherence, edu_score=edu.coherence.score, edu_reason=edu.coherence.reason)
        goal_dim = _merge_dimension(rule.goal_alignment, edu_score=edu.goal_alignment.score, edu_reason=edu.goal_alignment.reason)
        interaction_dim = _merge_dimension(
            rule.interaction,
            edu_score=edu.interaction_quality.score,
            edu_reason=edu.interaction_quality.reason,
            min_confidence=0.25,
        )
        semantic_task_met = semantic_task_met and edu.task_response.score >= 0.55

        cefr_note = f"Observed CEFR estimate: {edu.observed_cefr_estimate}"
        if edu.cefr_reason:
            cefr_note = f"{cefr_note} — {edu.cefr_reason}"
        cefr_dim = replace(
            rule.cefr_validation,
            reason=cefr_note,
            limitations=rule.cefr_validation.limitations + ("Observed estimate is not an official promotion decision.",),
        )

        # Acoustic-claim guard: sanitize LLM pronunciation/prosody prose.
        _sanitize_acoustic_interpretation(
            edu.pronunciation_interpretation,
            allowed_issue_tags=rule.pronunciation.issue_tags,
            dimension="pronunciation",
        )
        _sanitize_acoustic_interpretation(
            edu.delivery_interpretation,
            allowed_issue_tags=rule.prosody.issue_tags,
            dimension="delivery",
        )

    # Pronunciation/prosody dimensions stay rule-owned (LLM cannot override acoustic gates).
    pronunciation_dim = rule.pronunciation_dimension
    fluency_dim = rule.fluency_delivery

    blockers = list(rule.revision_readiness.blockers)
    if edu is not None and edu.task_response.score < 0.45:
        if "task_response_insufficient" not in blockers:
            blockers.append("task_response_insufficient")

    ready = not blockers and task_dim.score >= 0.55 and grammar_dim.score >= 0.45
    revision_readiness = RevisionReadinessFacts(ready=ready, blockers=tuple(blockers))

    completion_blockers = list(blockers)
    if not semantic_task_met:
        completion_blockers.append("semantic_task_not_met")
    acoustic_boost = pronunciation_dim.score >= 0.7 or fluency_dim.score >= 0.7
    completion_eligible = not completion_blockers and ready and semantic_task_met
    if context.force_complete and not completion_eligible:
        completion_blockers.append("force_complete_blocked_by_semantic_gate")
    completion = CompletionEligibilityFacts(
        eligible=completion_eligible,
        reason="Semantic task and readiness gates passed." if completion_eligible else "Completion blocked — semantic separation enforced.",
        semantic_task_met=semantic_task_met,
        acoustic_only_boost_blocked=(not semantic_task_met) and acoustic_boost,
    )

    explanation = _merge_explanation(rule, edu)
    candidate_skills = build_candidate_skill_evidence(rule=rule, input=input, context=context, educational=edu)

    strengths = tuple(dict.fromkeys((*rule.strong_skills, *(edu.strengths if edu else ()))))
    weaknesses = tuple(dict.fromkeys((*rule.weak_skills, edu.major_learning_issue if edu and edu.major_learning_issue else "")))
    weaknesses = tuple(w for w in weaknesses if w)

    priority = explanation.priority_issue or (weaknesses[0] if weaknesses else "continue_practice")
    comparison = edu.previous_attempt_comparison if edu else ""

    return SpeakingEvaluationEngineResult(
        evaluation_id=context.evaluation_id,
        student_id=context.student_id,
        language_id=context.language_id,
        session_id=context.session_id,
        task_id=context.task_id,
        attempt_id=context.attempt_id,
        revision_number=context.revision_number,
        evaluated_at=context.evaluated_at,
        task_context=context.task,
        goal_context=context.goal,
        official_cefr_context=context.official_cefr,
        evidence_summary=rule.evidence_summary,
        task_response=task_dim,
        topic_understanding=topic_dim,
        pronunciation=pronunciation_dim,
        fluency_delivery=fluency_dim,
        grammar=grammar_dim,
        vocabulary=vocab_dim,
        coherence=coherence_dim,
        interaction=interaction_dim,
        goal_alignment=goal_dim,
        cefr_validation=cefr_dim,
        strengths=strengths,
        weaknesses=weaknesses,
        priority_issue=priority,
        revision_readiness=revision_readiness,
        completion_eligibility=completion,
        comparison_with_previous_attempt=comparison,
        educational_analysis=edu,
        candidate_skill_evidence=candidate_skills,
        explanation=explanation,
        provider_provenance=input.provider_provenance,
        weak_skills=rule.weak_skills,
        strong_skills=rule.strong_skills,
        overall_readiness=rule.overall_readiness,
        engine_version=HYBRID_ENGINE_VERSION,
    )
