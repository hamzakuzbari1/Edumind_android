"""Prompt Builder (W4) — structured prompts from blueprint only; no LLM calls in W4."""

from __future__ import annotations

from app.services.language_writing_curriculum.goal_profiles import profile_for_goal
from app.services.language_writing_lesson_planner.types import WritingLessonBlueprint
from app.services.language_writing_generation.prompt_builder_types import (
    PROMPT_BUILDER_VERSION,
    PromptSectionKey,
    WritingPromptBundle,
    WritingPromptSection,
)


def build_prompt_from_blueprint(blueprint: WritingLessonBlueprint) -> WritingPromptBundle:
    """Build structured LLM prompt sections from blueprint — no educational decisions."""
    grammar_lines = [
        f"Primary focus: {blueprint.grammar_targets.primary}",
        f"Secondary: {blueprint.grammar_targets.secondary}" if blueprint.grammar_targets.secondary else "",
        f"Review: {blueprint.grammar_targets.review}" if blueprint.grammar_targets.review else "",
    ]
    vocab_lines = [
        f"Primary lemmas: {', '.join(blueprint.vocabulary_targets.primary)}",
        f"Secondary: {', '.join(blueprint.vocabulary_targets.secondary)}" if blueprint.vocabulary_targets.secondary else "",
    ]
    outcome_lines = [f"- {o}" for o in blueprint.learning_outcomes]
    criteria_lines = [f"- {c}" for c in blueprint.success_criteria_labels]
    constraint_lines = [
        f"Word count: {blueprint.success_criteria.min_words}–{blueprint.success_criteria.max_words}",
        f"Genre: {blueprint.genre}",
        f"Task type: {blueprint.task_type}",
        f"CEFR band: {blueprint.official_cefr.value}",
        f"Complexity level: {int(blueprint.context_complexity)}",
    ]

    profile = profile_for_goal(blueprint.personal_goal)
    style_lines = [f"- {d}" for d in profile.style_directives if d]

    sections = (
        WritingPromptSection(
            key=PromptSectionKey.system,
            content=(
                "You are a writing lesson content assistant. Generate natural student-facing "
                "wording only. Do not change educational targets, grammar focus, vocabulary list, "
                "outcomes, or success criteria defined in this prompt."
            ),
        ),
        WritingPromptSection(
            key=PromptSectionKey.role,
            content=f"Writing teacher for goal: {blueprint.goal_profile_label} ({blueprint.personal_goal.value}).",
        ),
        WritingPromptSection(
            key=PromptSectionKey.mission,
            content=(
                f"Situation: {blueprint.narrative_why}\n"
                f"Writing prompt seed: {blueprint.carry_forward_context or blueprint.narrative_why}\n"
                f"Mission style: {blueprint.mission_style.value}"
                + ("\nGoal style:\n" + "\n".join(style_lines) if style_lines else "")
            ),
        ),
        WritingPromptSection(
            key=PromptSectionKey.grammar,
            content="\n".join(line for line in grammar_lines if line),
        ),
        WritingPromptSection(
            key=PromptSectionKey.vocabulary,
            content="\n".join(line for line in vocab_lines if line),
        ),
        WritingPromptSection(
            key=PromptSectionKey.output_format,
            content=f"Expected output: {blueprint.expected_writing_output.value}",
        ),
        WritingPromptSection(
            key=PromptSectionKey.constraints,
            content="\n".join(constraint_lines),
        ),
        WritingPromptSection(
            key=PromptSectionKey.success_criteria,
            content="Required outcomes:\n" + "\n".join(outcome_lines) + "\n\nChecklist:\n" + "\n".join(criteria_lines),
        ),
        WritingPromptSection(
            key=PromptSectionKey.rules,
            content=(
                "Preserve all educational objectives exactly. "
                "Do not introduce new grammar structures or vocabulary beyond the blueprint. "
                "Do not access student data or progression. "
                "Rephrase for clarity only; objectives must remain identical."
            ),
        ),
    )
    return WritingPromptBundle(
        sections=sections,
        blueprint_id=blueprint.blueprint_id,
        blueprint_version=blueprint.blueprint_version,
        blueprint_hash=blueprint.blueprint_hash,
        builder_version=PROMPT_BUILDER_VERSION,
    )
