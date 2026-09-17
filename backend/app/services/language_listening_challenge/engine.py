"""Challenge-aware listening recommendation orchestration (Phase 3.3)."""

from __future__ import annotations

from app.services.language_learning_goal.profiles import profile_for_goal
from app.services.language_learning_goal.prompt import goal_objective_hints
from app.services.language_learning_goal.resolver import enrich_topics_for_goal
from app.services.language_learning_goal.scoring import DEFAULT_GOAL_INFLUENCE, score_goal_alignment
from app.services.language_learning_goal.types import GoalAwareRecommendation, LearningGoal
from app.services.language_listening_challenge.constants import CHALLENGE_INFLUENCE
from app.services.language_listening_challenge.scoring import (
    blend_with_challenge,
    compute_challenge_score,
    map_challenge_to_difficulty_band,
    plan_challenge_match_score,
)
from app.services.language_listening_challenge.types import ChallengeAwareRecommendation, ChallengeState
from app.services.language_listening_confidence.adapter import confidence_to_objective_progress
from app.services.language_listening_confidence.constants import CONFIDENCE_INFLUENCE
from app.services.language_listening_confidence.engine import recommend_confidence_aware_listening_plan
from app.services.language_listening_confidence.evidence import plan_evidence_fill_score
from app.services.language_listening_confidence.objectives import (
    confidence_review_priority_score,
    has_review_due_confidence,
    objectives_for_lesson_confidence,
)
from app.services.language_listening_confidence.scoring import blend_with_confidence, confidence_factor_for_plan
from app.services.language_listening_confidence.types import ConfidenceState
from app.services.language_listening_confidence.update import apply_decay_to_state
from app.services.language_listening_curriculum.candidates import enumerate_intelligence_candidates
from app.services.language_listening_curriculum.engine import _curriculum_stage
from app.services.language_listening_curriculum.intent import pick_lesson_intent
from app.services.language_listening_curriculum.knowledge import knowledge_node_for_situation
from app.services.language_listening_curriculum.scoring import score_candidate
from app.services.language_listening_curriculum.skills import (
    _primary_weak_share,
    parse_weak_listening_skills,
    pick_skill_focus,
)
from app.services.language_listening_curriculum.types import CurriculumHistoryEntry, CurriculumRecommendation
from app.services.language_listening_intelligence import select_next_listening_plan
from app.services.language_listening_intelligence.types import ListeningHistoryEntry


def recommend_challenge_adaptive_listening_plan(
    level: str,
    intelligence_history: list[ListeningHistoryEntry],
    curriculum_history: list[CurriculumHistoryEntry],
    confidence_state: ConfidenceState,
    challenge_state: ChallengeState,
    *,
    learning_goal: LearningGoal = LearningGoal.general_english,
    themes: str = "",
    topics: str = "",
    weaknesses: list[str] | None = None,
    generation_index: int | None = None,
    goal_influence: float = DEFAULT_GOAL_INFLUENCE,
    confidence_influence: float = CONFIDENCE_INFLUENCE,
    challenge_influence: float = CHALLENGE_INFLUENCE,
) -> ChallengeAwareRecommendation:
    """Wrap confidence-aware scoring with adaptive challenge alignment (one step within CEFR)."""
    challenge_state.level = level
    challenge_state.challenge_score = compute_challenge_score(challenge_state, confidence_state)
    target_challenge = challenge_state.current_level
    effective_band = map_challenge_to_difficulty_band(target_challenge)

    profile = profile_for_goal(learning_goal)
    enriched_topics = enrich_topics_for_goal(topics, profile.vocabulary_domains)
    gen_idx = generation_index if generation_index is not None else len(curriculum_history)

    confidence_state.level = level
    confidence_state.lesson_index = max(confidence_state.lesson_index, gen_idx)
    apply_decay_to_state(confidence_state)

    weak_skills = parse_weak_listening_skills(weaknesses)
    recent_intents = [h.lesson_intent for h in curriculum_history]
    objective_progress = confidence_to_objective_progress(confidence_state)
    review_due = has_review_due_confidence(confidence_state, gen_idx)

    intent = pick_lesson_intent(
        recent_intents,
        review_due=review_due,
        has_weak_skills=bool(weak_skills),
        recent_primary_weak_share=_primary_weak_share(curriculum_history, weak_skills),
    )
    objectives, review_objectives, _ = objectives_for_lesson_confidence(
        confidence_state,
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

    def _build(plan) -> tuple[CurriculumRecommendation, GoalAwareRecommendation, float, float, float]:
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
        review_boost = confidence_review_priority_score(objectives, confidence_state, gen_idx)
        cur_score_total = min(1.0, cur_score.total * 0.92 + review_boost * 0.08)

        goal_score = score_goal_alignment(
            plan,
            profile,
            selected_objectives=objectives + hints,
            curriculum_history=curriculum_history,
            intelligence_history=intelligence_history,
        )
        conf_factor = confidence_factor_for_plan(
            confidence_state, objectives, skill_focus, plan=plan
        )
        evidence_fill = plan_evidence_fill_score(
            narrative_format=plan.narrative_format.value,
            format_hint=plan.format_hint.value,
            category=plan.category.value,
            situation=plan.situation.value,
            difficulty_band=plan.difficulty_band.value,
            speaker_count=plan.speaker_count,
            pace=plan.pace.value,
            target_objectives=objectives + skill_focus,
            state=confidence_state,
        )
        conf_blended, _ = blend_with_confidence(
            cur_score_total,
            goal_score.total,
            conf_factor,
            goal_influence=goal_influence,
            confidence_influence=confidence_influence,
            evidence_factor=evidence_fill,
        )
        ch_match = plan_challenge_match_score(plan, target_challenge)
        final_blended, ch_w = blend_with_challenge(
            conf_blended, ch_match, challenge_influence=challenge_influence
        )

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
                f"challenge intent={intent.value} cur={cur_score_total:.2f} "
                f"goal={goal_score.total:.2f} conf={conf_factor:.2f} evidence={evidence_fill:.2f} "
                f"challenge={ch_match:.2f} blended={final_blended:.2f}"
            ),
        )
        goal_rec = GoalAwareRecommendation(
            recommendation=rec,
            learning_goal=learning_goal,
            goal_profile_label=profile.label,
            goal_alignment=goal_score,
            blended_score=conf_blended,
            goal_influence_pct=goal_influence,
            goal_objective_hints=hints,
            selection_reason=rec.selection_reason,
        )
        return rec, goal_rec, conf_factor, ch_match, final_blended

    if not candidates:
        conf_rec = recommend_confidence_aware_listening_plan(
            level,
            intelligence_history,
            curriculum_history,
            confidence_state,
            learning_goal=learning_goal,
            themes=themes,
            topics=topics,
            weaknesses=weaknesses,
            generation_index=gen_idx,
            goal_influence=goal_influence,
            confidence_influence=confidence_influence,
        )
        ch_match = plan_challenge_match_score(conf_rec.plan, target_challenge)
        final_blended, ch_w = blend_with_challenge(
            conf_rec.blended_score, ch_match, challenge_influence=challenge_influence
        )
        return ChallengeAwareRecommendation(
            confidence_aware=conf_rec,
            challenge_state=challenge_state,
            challenge_boost=ch_match,
            blended_score=final_blended,
            challenge_influence_pct=ch_w,
            effective_difficulty_band=effective_band,
            challenge_level=target_challenge,
            selection_reason="no_candidates_fallback",
        )

    best_rec: CurriculumRecommendation | None = None
    best_goal: GoalAwareRecommendation | None = None
    best_conf = 0.0
    best_ch = 0.0
    best_blended = -1.0
    for plan in candidates:
        rec, goal_rec, conf_factor, ch_match, blended = _build(plan)
        if blended > best_blended:
            best_rec, best_goal, best_conf, best_ch, best_blended = (
                rec,
                goal_rec,
                conf_factor,
                ch_match,
                blended,
            )

    assert best_rec is not None and best_goal is not None
    from app.services.language_listening_confidence.types import ConfidenceAwareRecommendation

    conf_rec = ConfidenceAwareRecommendation(
        recommendation=best_rec,
        goal_aware=best_goal,
        confidence_state=confidence_state,
        confidence_boost=best_conf,
        blended_score=best_goal.blended_score,
        confidence_influence_pct=confidence_influence,
        selection_reason=best_rec.selection_reason,
    )
    _, ch_w = blend_with_challenge(best_blended, best_ch, challenge_influence=challenge_influence)
    return ChallengeAwareRecommendation(
        confidence_aware=conf_rec,
        challenge_state=challenge_state,
        challenge_boost=best_ch,
        blended_score=best_blended,
        challenge_influence_pct=ch_w,
        effective_difficulty_band=effective_band,
        challenge_level=target_challenge,
        selection_reason=best_rec.selection_reason,
    )
