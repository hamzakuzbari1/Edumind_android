"""Goal-aware listening recommendation orchestration (Phase 3.1)."""

from __future__ import annotations

from app.services.language_learning_goal.profiles import profile_for_goal
from app.services.language_learning_goal.prompt import goal_objective_hints
from app.services.language_learning_goal.resolver import enrich_topics_for_goal
from app.services.language_learning_goal.scoring import (
    DEFAULT_GOAL_INFLUENCE,
    blend_scores,
    score_goal_alignment,
)
from app.services.language_learning_goal.types import GoalAwareRecommendation, LearningGoal
from app.services.language_listening_curriculum.candidates import enumerate_intelligence_candidates
from app.services.language_listening_curriculum.engine import _curriculum_stage
from app.services.language_listening_curriculum.intent import pick_lesson_intent
from app.services.language_listening_curriculum.knowledge import knowledge_node_for_situation
from app.services.language_listening_curriculum.objectives import (
    build_objective_progress,
    has_review_due,
    objectives_for_lesson,
)
from app.services.language_listening_curriculum.scoring import score_candidate
from app.services.language_listening_curriculum.skills import (
    _primary_weak_share,
    parse_weak_listening_skills,
    pick_skill_focus,
)
from app.services.language_listening_curriculum.types import CurriculumHistoryEntry, CurriculumRecommendation
from app.services.language_listening_intelligence import select_next_listening_plan
from app.services.language_listening_intelligence.types import ListeningHistoryEntry

GOAL_KEY = "listening_learning_goal"


def recommend_goal_aware_listening_plan(
    level: str,
    intelligence_history: list[ListeningHistoryEntry],
    curriculum_history: list[CurriculumHistoryEntry],
    *,
    learning_goal: LearningGoal,
    themes: str = "",
    topics: str = "",
    weaknesses: list[str] | None = None,
    generation_index: int | None = None,
    goal_influence: float = DEFAULT_GOAL_INFLUENCE,
) -> GoalAwareRecommendation:
    """Blend curriculum recommendation (85%) with goal alignment (15%) without modifying curriculum engine."""
    profile = profile_for_goal(learning_goal)
    enriched_topics = enrich_topics_for_goal(topics, profile.vocabulary_domains)
    gen_idx = generation_index if generation_index is not None else len(curriculum_history)

    weak_skills = parse_weak_listening_skills(weaknesses)
    recent_intents = [h.lesson_intent for h in curriculum_history]
    objective_progress = build_objective_progress(curriculum_history, level)
    review_due = has_review_due(objective_progress, gen_idx)

    intent = pick_lesson_intent(
        recent_intents,
        review_due=review_due,
        has_weak_skills=bool(weak_skills),
        recent_primary_weak_share=_primary_weak_share(curriculum_history, weak_skills),
    )
    objectives, review_objectives, _ = objectives_for_lesson(
        objective_progress,
        generation_index=gen_idx,
        intent=intent,
    )
    skill_focus = pick_skill_focus(
        level,
        curriculum_history=curriculum_history,
        weak_skills=weak_skills,
        intent=intent,
        objectives=objectives,
        generation_index=gen_idx,
    )
    hints = goal_objective_hints(profile, objectives)

    candidates = enumerate_intelligence_candidates(
        level,
        intelligence_history,
        themes=themes,
        topics=enriched_topics,
        generation_index=gen_idx,
    )

    def _build(plan) -> tuple[CurriculumRecommendation, GoalAlignmentScore, float]:
        knowledge_node = knowledge_node_for_situation(plan.situation)
        cur_score = score_candidate(
            plan,
            level=level,
            intelligence_history=intelligence_history,
            curriculum_history=curriculum_history,
            objective_progress=objective_progress,
            weak_skills=weak_skills,
            skill_focus=skill_focus,
            objectives=objectives,
            intent=intent,
            recent_intents=recent_intents,
            themes=themes,
            topics=enriched_topics,
            generation_index=gen_idx,
        )
        goal_score = score_goal_alignment(
            plan,
            profile,
            selected_objectives=objectives + hints,
            curriculum_history=curriculum_history,
            intelligence_history=intelligence_history,
        )
        blended = blend_scores(cur_score.total, goal_score.total, goal_influence=goal_influence)
        rec = CurriculumRecommendation(
            plan=plan,
            skill_focus=skill_focus,
            objectives=objectives,
            knowledge_node=knowledge_node,
            review_objectives=review_objectives,
            score=cur_score,
            curriculum_stage=_curriculum_stage(objective_progress),
            lesson_intent=intent.value,
            selection_reason=(
                f"goal={learning_goal.value} intent={intent.value} "
                f"curriculum={cur_score.total:.2f} goal={goal_score.total:.2f} blended={blended:.2f}"
            ),
        )
        return rec, goal_score, blended

    if not candidates:
        plan = select_next_listening_plan(
            level,
            intelligence_history,
            themes=themes,
            topics=enriched_topics,
            generation_index=gen_idx,
        )
        rec, goal_score, blended = _build(plan)
        return GoalAwareRecommendation(
            recommendation=rec,
            learning_goal=learning_goal,
            goal_profile_label=profile.label,
            goal_alignment=goal_score,
            blended_score=blended,
            goal_influence_pct=goal_influence,
            goal_objective_hints=hints,
            selection_reason="no_candidates_fallback",
        )

    best_rec: CurriculumRecommendation | None = None
    best_goal: GoalAlignmentScore | None = None
    best_blended = -1.0
    for plan in candidates:
        rec, goal_score, blended = _build(plan)
        if blended > best_blended:
            best_rec, best_goal, best_blended = rec, goal_score, blended

    assert best_rec is not None and best_goal is not None
    return GoalAwareRecommendation(
        recommendation=best_rec,
        learning_goal=learning_goal,
        goal_profile_label=profile.label,
        goal_alignment=best_goal,
        blended_score=best_blended,
        goal_influence_pct=goal_influence,
        goal_objective_hints=hints,
        selection_reason=best_rec.selection_reason,
    )
