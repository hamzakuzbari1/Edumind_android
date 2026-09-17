"""Hybrid Writing Evaluation Engine — rules + Claude educational analysis → canonical result."""

from __future__ import annotations

import asyncio

from app.services.language_writing_educational_analyzer.analyzer import analyze_writing_draft_educationally
from app.services.language_writing_educational_analyzer.types import EducationalAnalysisContext
from app.services.language_writing_evaluator.blueprint_snapshot import EvaluatorBlueprintSnapshot
from app.services.language_writing_evaluator.evaluation_result import (
    EVALUATION_RESULT_VERSION,
    WritingEvaluationEngineResult,
)
from app.services.language_writing_evaluator.hybrid_merge import merge_hybrid_evaluation
from app.services.language_writing_evaluator.rule_engine import RULE_ENGINE_VERSION, compute_rule_evaluation_facts, word_count
from app.services.language_writing_evaluator.rule_facts_types import RuleEvaluationFacts

EVALUATOR_RUNTIME_VERSION = EVALUATION_RESULT_VERSION
HYBRID_ENGINE_VERSION = EVALUATION_RESULT_VERSION


def _goal_label(personal_goal: str) -> str:
    return (personal_goal or "general_english").replace("_", " ").strip().title()


def _analysis_context(
    *,
    blueprint: EvaluatorBlueprintSnapshot,
    rule: RuleEvaluationFacts,
    official_cefr: str,
    writing_prompt: str,
    revision_number: int,
    previous: WritingEvaluationEngineResult | None,
) -> EducationalAnalysisContext:
    criteria = tuple((c.label, c.status.value) for c in rule.success_criteria[:12])
    rule_summary = (
        f"Rule engine (for context only — do not override): "
        f"grammar_passed={rule.grammar.passed}, "
        f"vocab_passed={rule.vocabulary.passed}, "
        f"word_count={rule.word_count}, "
        f"meets_word_limit={rule.meets_word_limit}, "
        f"ready={rule.revision_readiness.ready}"
    )
    previous_cefr = ""
    previous_task_score = 0.0
    if previous is not None:
        if previous.claude_analysis is not None:
            previous_cefr = previous.claude_analysis.cefr_estimate
            previous_task_score = previous.claude_analysis.task_response.score
        if not previous_cefr:
            previous_cefr = previous.cefr_validation.expected_band
    personal_goal = blueprint.personal_goal or "general_english"
    return EducationalAnalysisContext(
        official_cefr=official_cefr,
        writing_prompt=writing_prompt,
        chain_node_id=blueprint.chain_node_id,
        genre=blueprint.genre,
        task_type=blueprint.task_type,
        narrative_why=blueprint.narrative_why,
        grammar_primary=blueprint.grammar_primary,
        vocabulary_primary=blueprint.vocabulary_primary,
        learning_outcomes=blueprint.learning_outcomes,
        success_criteria=criteria,
        rule_summary=rule_summary,
        personal_goal=personal_goal,
        goal_label=_goal_label(personal_goal),
        revision_number=revision_number,
        previous_cefr=previous_cefr,
        previous_task_score=previous_task_score,
    )


async def evaluate_writing_draft(
    draft_text: str,
    *,
    draft_id: str,
    revision_number: int,
    blueprint: EvaluatorBlueprintSnapshot,
    official_cefr: str = "B1",
    previous: WritingEvaluationEngineResult | None = None,
    writing_prompt: str = "",
) -> WritingEvaluationEngineResult:
    """Hybrid evaluation: rule engine → Claude analyzer → canonical merge."""
    rule = compute_rule_evaluation_facts(
        draft_text,
        draft_id=draft_id,
        revision_number=revision_number,
        blueprint=blueprint,
        official_cefr=official_cefr,
    )
    claude = await analyze_writing_draft_educationally(
        draft_text=draft_text,
        context=_analysis_context(
            blueprint=blueprint,
            rule=rule,
            official_cefr=official_cefr,
            writing_prompt=writing_prompt,
            revision_number=revision_number,
            previous=previous,
        ),
    )
    return merge_hybrid_evaluation(rule, claude, previous=previous)


def evaluate_writing_draft_sync(
    draft_text: str,
    *,
    draft_id: str,
    revision_number: int,
    blueprint: EvaluatorBlueprintSnapshot,
    official_cefr: str = "B1",
    previous: WritingEvaluationEngineResult | None = None,
    writing_prompt: str = "",
) -> WritingEvaluationEngineResult:
    """Synchronous entry for scripts/tests."""
    return asyncio.run(
        evaluate_writing_draft(
            draft_text,
            draft_id=draft_id,
            revision_number=revision_number,
            blueprint=blueprint,
            official_cefr=official_cefr,
            previous=previous,
            writing_prompt=writing_prompt,
        )
    )


def evaluate_draft(
    draft_text: str,
    *,
    draft_id: str,
    revision_number: int,
    blueprint: EvaluatorBlueprintSnapshot,
) -> tuple:
    """Deprecated adapter."""
    result = evaluate_writing_draft_sync(
        draft_text,
        draft_id=draft_id,
        revision_number=revision_number,
        blueprint=blueprint,
    )
    return result.to_coach_evaluation(), result.to_evaluation_facts()
