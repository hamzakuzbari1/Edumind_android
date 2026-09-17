"""Deterministic lesson-shape policies (G3.1).

No LLM. No randomness. Review never blocks today's grammar lesson.
"""

from __future__ import annotations

from app.services.language_grammar.enums import (
    GrammarLessonStepKind,
    GrammarMasteryState,
    GrammarReinforcementSkill,
)
from app.services.language_grammar_integration.types import (
    GrammarLearningSnapshot,
    GrammarMasteryPlanSummary,
    GrammarTopicPlanMeta,
)

DEFAULT_POLICY_ID = "default_lesson_v1"

# Canonical relative order — lower must appear before higher when both present.
# Skill-specific reinforcements share one band so catalog skill order is free.
STEP_ORDER_RANK: dict[GrammarLessonStepKind, int] = {
    GrammarLessonStepKind.warmup: 10,
    GrammarLessonStepKind.quick_review: 20,
    GrammarLessonStepKind.explanation: 30,
    GrammarLessonStepKind.practice: 40,
    GrammarLessonStepKind.reinforcement: 50,
    GrammarLessonStepKind.reading_reinforcement: 50,
    GrammarLessonStepKind.listening_reinforcement: 50,
    GrammarLessonStepKind.writing_reinforcement: 50,
    GrammarLessonStepKind.speaking_reinforcement: 50,
    GrammarLessonStepKind.exit_check: 60,
    GrammarLessonStepKind.summary: 70,
    GrammarLessonStepKind.homework: 80,
}

STEP_DURATION: dict[GrammarLessonStepKind, int] = {
    GrammarLessonStepKind.warmup: 3,
    GrammarLessonStepKind.quick_review: 4,
    GrammarLessonStepKind.explanation: 6,
    GrammarLessonStepKind.practice: 8,
    GrammarLessonStepKind.reinforcement: 5,
    GrammarLessonStepKind.reading_reinforcement: 5,
    GrammarLessonStepKind.listening_reinforcement: 5,
    GrammarLessonStepKind.writing_reinforcement: 5,
    GrammarLessonStepKind.speaking_reinforcement: 5,
    GrammarLessonStepKind.exit_check: 3,
    GrammarLessonStepKind.summary: 2,
    GrammarLessonStepKind.homework: 1,
}

_SKILL_TO_KIND: dict[GrammarReinforcementSkill, GrammarLessonStepKind] = {
    GrammarReinforcementSkill.reading: GrammarLessonStepKind.reading_reinforcement,
    GrammarReinforcementSkill.listening: GrammarLessonStepKind.listening_reinforcement,
    GrammarReinforcementSkill.writing: GrammarLessonStepKind.writing_reinforcement,
    GrammarReinforcementSkill.speaking: GrammarLessonStepKind.speaking_reinforcement,
}


def skill_to_reinforcement_kind(skill: GrammarReinforcementSkill) -> GrammarLessonStepKind:
    return _SKILL_TO_KIND[skill]


def duration_budget(snapshot: GrammarLearningSnapshot) -> int:
    """Fatigue budget is a placeholder clamp — deterministic."""
    return max(15, min(60, int(snapshot.fatigue_budget_minutes)))


def needs_warmup(mastery: GrammarMasteryPlanSummary | None) -> bool:
    if mastery is None:
        return True
    if mastery.state in (GrammarMasteryState.unknown, GrammarMasteryState.learning):
        return True
    return mastery.overall_mastery < 40.0


def select_quick_review_id(snapshot: GrammarLearningSnapshot, focus_id: str) -> str | None:
    """Review never blocks today's lesson — at most one quick review of a different topic."""
    for item in snapshot.review_queue:
        if item.grammar_id and item.grammar_id != focus_id:
            return item.grammar_id
    return None


def select_reinforcement_skills(
    topic: GrammarTopicPlanMeta,
    mastery: GrammarMasteryPlanSummary | None,
    *,
    budget_remaining: int,
) -> tuple[GrammarReinforcementSkill, ...]:
    """Pick ordered reinforcements from catalog best_reinforcement_skills within budget."""
    preferred = tuple(topic.best_reinforcement_skills)
    if not preferred:
        preferred = (
            GrammarReinforcementSkill.reading,
            GrammarReinforcementSkill.writing,
        )

    # Context diversity pressure: prefer more skills when under minimum contexts.
    min_ctx = max(1, int(topic.minimum_context_diversity))
    have_ctx = int(mastery.distinct_context_count) if mastery else 0
    max_skills = 2 if have_ctx >= min_ctx else min(3, len(preferred))
    if budget_remaining < 10:
        max_skills = 1
    if budget_remaining < 5:
        return ()

    chosen: list[GrammarReinforcementSkill] = []
    cost = STEP_DURATION[GrammarLessonStepKind.reading_reinforcement]
    for skill in preferred:
        if len(chosen) >= max_skills:
            break
        if budget_remaining < cost * (len(chosen) + 1):
            break
        if skill not in chosen:
            chosen.append(skill)
    return tuple(chosen)


def context_hint_for(topic: GrammarTopicPlanMeta, index: int) -> str | None:
    contexts = topic.recommended_contexts
    if not contexts:
        return None
    return contexts[index % len(contexts)]


def lesson_goal_for(topic: GrammarTopicPlanMeta) -> str:
    if topic.learning_objectives:
        return topic.learning_objectives[0]
    if topic.focus_note:
        return topic.focus_note
    return f"Practice {topic.display_name}"


def practice_item_count(mastery: GrammarMasteryPlanSummary | None) -> int:
    if mastery is None or mastery.state is GrammarMasteryState.unknown:
        return 4
    if mastery.state is GrammarMasteryState.learning:
        return 5
    if mastery.overall_mastery >= 75.0:
        return 3
    return 4
