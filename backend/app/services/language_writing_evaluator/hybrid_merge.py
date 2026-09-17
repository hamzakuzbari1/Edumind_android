"""Merge rule facts + Claude educational facts into canonical WritingEvaluationEngineResult."""

from __future__ import annotations

from dataclasses import replace

from app.services.language_writing_educational_analyzer.types import ClaudeEducationalFacts
from app.services.language_writing_evaluator.evaluation_result import (
    EVALUATION_RESULT_VERSION,
    ExplanationFacts,
    WritingEvaluationEngineResult,
)
from app.services.language_writing_evaluator.rule_facts_types import RuleEvaluationFacts
from app.services.language_writing_revision.comparison import compare_evaluation_facts

HYBRID_ENGINE_VERSION = EVALUATION_RESULT_VERSION


def _merge_explanation(
    rule: RuleEvaluationFacts,
    claude: ClaudeEducationalFacts | None,
) -> ExplanationFacts:
    """Enrich the rule explanation with Claude's teacher-like facts.

    Claude only adds educational text (grammar coaching, vocabulary, idea/topic
    insight, diagnosis, one revision mission). The rule engine keeps ownership of
    readiness and pass/fail — none of those are touched here.
    """
    expl = rule.explanation
    if claude is None or not claude.available:
        return expl

    improvements: list[str] = list(expl.improvements)

    def _add(line: str) -> None:
        line = (line or "").strip()
        if line and line not in improvements:
            improvements.append(line)

    # Grammar coaching (why / rule / fix / example) — highest teaching value.
    for note in claude.grammar_notes[:3]:
        _add(note.to_feedback_line())

    # Task / topic gaps.
    if claude.task_response.score < 0.6 and claude.task_response.reason:
        _add(claude.task_response.reason)
    if claude.topic_understanding.score < 0.5 and claude.topic_understanding.reason:
        _add(claude.topic_understanding.reason)

    # Idea development and organization coaching.
    if claude.idea_development.score < 0.6 and claude.idea_development.reason:
        _add(claude.idea_development.reason)
    if claude.organization.score < 0.6 and claude.organization.reason:
        _add(claude.organization.reason)
    if claude.coherence.score < 0.6 and claude.coherence.reason:
        _add(claude.coherence.reason)

    # Vocabulary coaching.
    for suggestion in claude.vocabulary.suggestions[:2]:
        _add(suggestion)
    if claude.vocabulary.score < 0.55 and claude.vocabulary.range_comment:
        _add(claude.vocabulary.range_comment)

    # Goal alignment coaching.
    if claude.goal_alignment.score < 0.55 and claude.goal_alignment.reason:
        _add(claude.goal_alignment.reason)

    # One clear next mission.
    if claude.revision_priority:
        _add(claude.revision_priority)

    # Priority / focus text (descriptive only — never a pass/fail decision).
    priority = expl.priority_issue
    focus = expl.focus_label
    if not rule.grammar.errors:
        if claude.learning_diagnosis:
            priority = claude.learning_diagnosis
        if claude.major_learning_issue:
            focus = claude.major_learning_issue
    if not priority and claude.learning_diagnosis:
        priority = claude.learning_diagnosis

    # Summary enrichment with the educational diagnosis.
    summary = expl.summary
    diagnosis = claude.learning_diagnosis or claude.task_response.reason
    if diagnosis and not rule.revision_readiness.ready:
        summary = f"{expl.summary} Teacher analysis: {diagnosis}".strip()

    # Strengths: genuine, specific wins from the teacher read.
    strengths = list(expl.strengths)
    for strength in claude.strengths:
        if strength and strength not in strengths:
            strengths.append(strength)
    if claude.task_response.score >= 0.75 and claude.task_response.reason:
        line = f"Task response: {claude.task_response.reason}"
        if line not in strengths:
            strengths.insert(0, line)

    return ExplanationFacts(
        summary=summary,
        priority_issue=priority,
        improvements=tuple(dict.fromkeys(improvements))[:8],
        strengths=tuple(dict.fromkeys(strengths))[:4],
        focus_label=focus,
    )


def merge_hybrid_evaluation(
    rule: RuleEvaluationFacts,
    claude: ClaudeEducationalFacts | None,
    *,
    previous: WritingEvaluationEngineResult | None = None,
) -> WritingEvaluationEngineResult:
    """Canonical merge — pass/fail/readiness from rules only; Claude enriches explanation."""
    cefr = rule.cefr_validation
    if claude and claude.available and claude.cefr_estimate:
        note = f"Claude observed band: {claude.cefr_estimate}"
        if claude.cefr_reason:
            note = f"{note} — {claude.cefr_reason}"
        notes = tuple(dict.fromkeys((*cefr.notes, note)))
        cefr = replace(cefr, notes=notes)

    explanation = _merge_explanation(rule, claude)

    result = WritingEvaluationEngineResult(
        draft_id=rule.draft_id,
        revision_number=rule.revision_number,
        chain_node_id=rule.chain_node_id,
        blueprint_version=rule.blueprint_version,
        blueprint_hash=rule.blueprint_hash,
        generation_hash=rule.generation_hash,
        word_count=rule.word_count,
        meets_word_limit=rule.meets_word_limit,
        grammar=rule.grammar,
        vocabulary=rule.vocabulary,
        organization=rule.organization,
        task_completion=rule.task_completion,
        goal_alignment=rule.goal_alignment,
        cefr_validation=cefr,
        success_criteria=rule.success_criteria,
        learning_outcomes=rule.learning_outcomes,
        revision_readiness=rule.revision_readiness,
        completion=rule.completion,
        comparison=None,
        explanation=explanation,
        confidence=rule.confidence,
        weak_skills=rule.weak_skills,
        strong_skills=rule.strong_skills,
        critical_mistakes=rule.critical_mistakes,
        overall_readiness=rule.overall_readiness,
        claude_analysis=claude if claude and claude.available else None,
        engine_version=HYBRID_ENGINE_VERSION,
    )

    if previous is not None:
        comparison = compare_evaluation_facts(
            previous.to_evaluation_facts(),
            result.to_evaluation_facts(),
        )
        result = replace(result, comparison=comparison)
    return result
