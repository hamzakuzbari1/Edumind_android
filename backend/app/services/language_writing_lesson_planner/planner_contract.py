"""Deterministic blueprint assembly (W3.1 FROZEN) — merges catalog + goal + progression; no LLM."""

from __future__ import annotations

from dataclasses import replace

from app.services.language_writing.enums import WritingGoal
from app.services.language_writing_lesson_planner.blueprint_hash import compute_blueprint_hash
from app.services.language_writing_lesson_planner.types import (
    BLUEPRINT_COMPATIBILITY_NOTES,
    BLUEPRINT_SCHEMA_VERSION,
    BLUEPRINT_VERSION,
    EvaluationPlan,
    GrammarTargets,
    LessonPlannerInput,
    LessonPlannerResult,
    LessonTimePlan,
    StructuredSuccessCriteria,
    VocabularyTargets,
    WritingLessonBlueprint,
    success_criteria_labels,
)


def _stretch_grammar(primary: str, secondary: str) -> str:
    if secondary and secondary != primary:
        return secondary
    return ""


def _stretch_vocab(secondary: tuple[str, ...], review: tuple[str, ...]) -> tuple[str, ...]:
    combined = secondary + review
    return combined[:2] if combined else ()


def _evaluation_weights(goal: WritingGoal) -> tuple[float, float, float, float, float]:
    """Return grammar, vocabulary, organization, task_completion, goal_alignment weights."""
    if goal in (WritingGoal.ielts, WritingGoal.academic):
        return (0.20, 0.20, 0.25, 0.20, 0.15)
    if goal in (WritingGoal.business, WritingGoal.job_interview):
        return (0.15, 0.15, 0.25, 0.25, 0.20)
    if goal == WritingGoal.creative_writing:
        return (0.15, 0.20, 0.20, 0.20, 0.25)
    return (0.25, 0.20, 0.20, 0.20, 0.15)


def _build_evaluation_plan(
    *,
    goal: WritingGoal,
    learning_outcomes: tuple[str, ...],
    common_mistakes: tuple[str, ...],
    stretch_targets: tuple[str, ...],
) -> EvaluationPlan:
    gw, vw, ow, tw, aw = _evaluation_weights(goal)
    critical = tuple(m for m in common_mistakes if m.startswith(("tone:", "grammar:", "task:")))[:4]
    if not critical:
        critical = common_mistakes[:3]
    stretch_bonus = stretch_targets[:3] if stretch_targets else learning_outcomes[-1:]
    return EvaluationPlan(
        grammar_weight=gw,
        vocabulary_weight=vw,
        organization_weight=ow,
        task_completion_weight=tw,
        goal_alignment_weight=aw,
        required_outcomes=learning_outcomes,
        critical_mistakes=critical,
        stretch_bonus_criteria=stretch_bonus,
    )


def _build_structured_success_criteria(
    *,
    min_words: int,
    max_words: int,
    grammar: GrammarTargets,
    vocab: VocabularyTargets,
    expected_output,
    learning_outcomes: tuple[str, ...],
) -> StructuredSuccessCriteria:
    required_grammar = tuple(filter(None, (grammar.primary, grammar.secondary)))
    return StructuredSuccessCriteria(
        min_words=min_words,
        max_words=max_words,
        required_grammar=required_grammar,
        required_vocabulary=vocab.primary,
        required_output_format=expected_output,
        required_objectives=learning_outcomes[:3],
        optional_stretch_objectives=learning_outcomes[3:],
    )


def assemble_blueprint(input_ctx: LessonPlannerInput) -> LessonPlannerResult:
    """Deterministically assemble a blueprint from planner inputs — no LLM."""
    node = input_ctx.selected_node
    profile = input_ctx.goal_profile
    time = node.time_estimate
    writing_min = time.writing_minutes if time else 12
    revision_min = time.revision_minutes if time else 6
    personality = profile.coach_defaults.personality

    grammar = GrammarTargets(
        primary=node.grammar_focus_primary,
        secondary=node.grammar_focus_secondary,
        review=node.grammar_focus_review,
        stretch=_stretch_grammar(node.grammar_focus_primary, node.grammar_focus_secondary),
    )
    vocab = VocabularyTargets(
        primary=node.vocabulary_primary,
        secondary=node.vocabulary_secondary,
        review=node.vocabulary_review,
        stretch=_stretch_vocab(node.vocabulary_secondary, node.vocabulary_review),
        categories=node.vocabulary_categories or profile.preferred_vocabulary_categories,
    )
    review_targets = tuple(filter(None, (node.grammar_focus_review, *node.vocabulary_review)))
    stretch_targets = tuple(filter(None, (grammar.stretch, *vocab.stretch)))
    min_words = max(40, int(60 * profile.word_target_multiplier))
    max_words = max(120, int(180 * profile.word_target_multiplier))

    structured = _build_structured_success_criteria(
        min_words=min_words,
        max_words=max_words,
        grammar=grammar,
        vocab=vocab,
        expected_output=node.expected_output,
        learning_outcomes=node.learning_outcomes,
    )
    labels = success_criteria_labels(structured)
    evaluation = _build_evaluation_plan(
        goal=profile.goal,
        learning_outcomes=node.learning_outcomes,
        common_mistakes=node.common_mistakes,
        stretch_targets=stretch_targets,
    )

    draft = WritingLessonBlueprint(
        blueprint_id=input_ctx.blueprint_id or f"{node.chain_id}:{node.node_id}",
        blueprint_version=BLUEPRINT_VERSION,
        schema_version=BLUEPRINT_SCHEMA_VERSION,
        compatibility_notes=BLUEPRINT_COMPATIBILITY_NOTES,
        blueprint_hash="",
        official_cefr=input_ctx.official_cefr,
        personal_goal=profile.goal,
        goal_profile_label=profile.label,
        topic_id=node.topic_id,
        chain_id=node.chain_id,
        chain_node_id=node.node_id,
        chain_position=node.position,
        curriculum_arc=node.arc_stage,
        context_complexity=node.context_complexity,
        task_type=node.task_type,
        genre=node.genre,
        grammar_targets=grammar,
        vocabulary_targets=vocab,
        mission_style=profile.preferred_mission_style,
        expected_writing_output=node.expected_output,
        difficulty_drivers=node.difficulty_drivers,
        learning_outcomes=node.learning_outcomes,
        success_criteria=structured,
        success_criteria_labels=labels,
        evaluation_plan=evaluation,
        common_mistakes=node.common_mistakes,
        review_targets=review_targets,
        stretch_targets=stretch_targets,
        time_plan=LessonTimePlan(
            writing_minutes=writing_min,
            revision_minutes=revision_min,
            total_minutes=writing_min + revision_min,
        ),
        min_words=min_words,
        max_words=max_words,
        coach_personality=personality,
        narrative_why=node.narrative_why,
        carry_forward_context=node.carry_forward_template,
    )
    blueprint = replace(draft, blueprint_hash=compute_blueprint_hash(draft))
    reason = f"Planned node {node.node_id} on chain {node.chain_id} for goal {profile.goal.value}"
    return LessonPlannerResult(blueprint=blueprint, selection_reason=reason)
