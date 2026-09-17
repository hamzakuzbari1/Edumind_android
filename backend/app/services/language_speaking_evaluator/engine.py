"""Hybrid Speaking Evaluation Engine — rules + Claude → canonical result (S7)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.services.language_speaking_educational_analyzer.analyzer import analyze_speaking_turn_educationally
from app.services.language_speaking_educational_analyzer.types import SpeakingAnalysisContext
from app.services.language_speaking_evaluator.evaluation_result import SPEAKING_EVALUATION_RESULT_VERSION, SpeakingEvaluationEngineResult
from app.services.language_speaking_evaluator.hybrid_merge import merge_speaking_evaluation
from app.services.language_speaking_evaluator.input_types import SpeakingEvaluationContext, SpeakingEvaluationInput
from app.services.language_speaking_evaluator.rule_engine import RULE_ENGINE_VERSION, evaluate_speaking_evidence

EVALUATOR_RUNTIME_VERSION = SPEAKING_EVALUATION_RESULT_VERSION
HYBRID_ENGINE_VERSION = SPEAKING_EVALUATION_RESULT_VERSION


def _rule_summary(rule) -> str:
    return (
        f"transcript_words={rule.transcript.word_count}; "
        f"task_overlap={rule.transcript.task_keyword_overlap_ratio:.2f}; "
        f"pron_issues={len(rule.pronunciation.issue_tags)}; "
        f"prosody_issues={len(rule.prosody.issue_tags)}; "
        f"ready={rule.revision_readiness.ready}"
    )


def _pronunciation_summary(rule) -> str:
    p = rule.pronunciation
    if not p.available:
        return "unavailable"
    return (
        f"substitutions={p.substitution_count}; omissions={p.omission_count}; "
        f"issues={', '.join(p.issue_tags[:6]) or 'none'}; reliability={p.reliability:.2f}"
    )


def _prosody_summary(rule) -> str:
    p = rule.prosody
    if not p.available:
        return "unavailable"
    return (
        f"pause_density={p.pause_density}; long_pauses={p.long_pause_count}; "
        f"issues={', '.join(p.issue_tags[:6]) or 'none'}; reliability={p.reliability:.2f}"
    )


def _analysis_context(
    *,
    input: SpeakingEvaluationInput,
    context: SpeakingEvaluationContext,
    rule,
) -> SpeakingAnalysisContext:
    avail = ", ".join(f"{k}={v}" for k, v in sorted(rule.evidence_summary.availability.items()))
    return SpeakingAnalysisContext(
        task_id=context.task.task_id,
        task_type=context.task.task_type,
        task_instructions=context.task.task_instructions,
        task_prompt=context.task.task_prompt,
        success_criteria=context.task.success_criteria,
        target_skill_ids=context.task.target_skill_ids,
        official_cefr=context.official_cefr.official_cefr,
        speaking_goal=context.goal.speaking_goal,
        goal_label=context.goal.goal_label,
        transcript=input.transcript_text,
        rule_summary=_rule_summary(rule),
        pronunciation_summary=_pronunciation_summary(rule),
        prosody_summary=_prosody_summary(rule),
        evidence_availability=avail,
        evidence_reliability=f"{rule.evidence_quality.overall_reliability:.2f}",
        revision_number=context.revision_number,
        previous_attempt_summary=context.previous_attempt_summary,
    )


async def evaluate_speaking_turn(
    input: SpeakingEvaluationInput,
    context: SpeakingEvaluationContext,
) -> SpeakingEvaluationEngineResult:
    """Hybrid evaluation: rule engine → Claude analyzer → canonical merge."""
    rule = evaluate_speaking_evidence(input, context)
    educational = await analyze_speaking_turn_educationally(
        context=_analysis_context(input=input, context=context, rule=rule),
    )
    return merge_speaking_evaluation(rule, educational, input=input, context=context)


def evaluate_speaking_turn_sync(
    input: SpeakingEvaluationInput,
    context: SpeakingEvaluationContext,
) -> SpeakingEvaluationEngineResult:
    return asyncio.run(evaluate_speaking_turn(input, context))


def new_evaluation_context(
    *,
    evaluation_id: str,
    student_id: int,
    language_id: int,
    session_id: str,
    task_id: str,
    attempt_id: str,
    revision_number: int,
    task,
    goal,
    official_cefr,
    previous_attempt_summary: str = "",
    force_complete: bool = False,
    evaluated_at: str | None = None,
) -> SpeakingEvaluationContext:
    return SpeakingEvaluationContext(
        evaluation_id=evaluation_id,
        student_id=student_id,
        language_id=language_id,
        session_id=session_id,
        task_id=task_id,
        attempt_id=attempt_id,
        revision_number=revision_number,
        evaluated_at=evaluated_at or datetime.now(tz=timezone.utc).isoformat(),
        task=task,
        goal=goal,
        official_cefr=official_cefr,
        previous_attempt_summary=previous_attempt_summary,
        force_complete=force_complete,
    )
