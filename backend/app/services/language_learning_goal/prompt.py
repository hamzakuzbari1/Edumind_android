"""Learning goal prompt block for listening generation (Phase 3.1)."""

from __future__ import annotations

from app.services.language_learning_goal.profiles import profile_for_goal
from app.services.language_learning_goal.types import LearningGoal, LearningGoalProfile
from app.services.language_listening_intelligence.types import ListeningIntelligencePlan


def goal_objective_hints(profile: LearningGoalProfile, selected_objectives: tuple[str, ...]) -> tuple[str, ...]:
    hints: list[str] = []
    for oid in profile.preferred_objectives:
        if oid not in selected_objectives and oid not in hints:
            hints.append(oid)
        if len(hints) >= 2:
            break
    return tuple(hints)


def build_learning_goal_prompt_block(
    goal: LearningGoal,
    *,
    plan: ListeningIntelligencePlan | None = None,
    objective_hints: tuple[str, ...] = (),
) -> str:
    """Build [LEARNING GOAL] directives — style adaptation without naming the learner's goal."""
    profile = profile_for_goal(goal)
    lines = ["[LEARNING GOAL]"]
    for directive in profile.style_directives:
        lines.append(f"- {directive}")

    if plan is not None:
        lines.append(
            f"- Situation register: {plan.situation.value.replace('_', ' ')} "
            f"with {plan.narrative_format.value.replace('_', ' ')} delivery."
        )
        if profile.vocabulary_domains:
            vocab = ", ".join(profile.vocabulary_domains[:5])
            lines.append(f"- Vocabulary domains to weave naturally: {vocab}.")
        if plan.pace.value in profile.preferred_pace:
            lines.append(f"- Speaking pace: {plan.pace.value.replace('_', ' ')}.")

    if objective_hints:
        hints = ", ".join(oid.replace("_", " ") for oid in objective_hints[:2])
        lines.append(f"- Subtly reinforce listening angles such as {hints} where the transcript allows.")

    lines.append(
        "Adapt transcript style to these constraints naturally. "
        "Do not state or reference the learner's study purpose explicitly."
    )
    lines.append("[/LEARNING GOAL]")
    return "\n".join(lines)
