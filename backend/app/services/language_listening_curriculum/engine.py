"""Curriculum engine orchestration and telemetry (Phase 2.3.1)."""

from __future__ import annotations

from collections import Counter

from app.services.language_listening_curriculum.candidates import enumerate_intelligence_candidates
from app.services.language_listening_curriculum.intent import LessonIntent, intent_distribution, pick_lesson_intent
from app.services.language_listening_curriculum.knowledge import knowledge_node_for_situation
from app.services.language_listening_curriculum.objective_catalog import catalog_for_level
from app.services.language_listening_curriculum.objectives import (
    build_objective_progress,
    has_review_due,
    level_objectives,
    objectives_for_lesson,
)
from app.services.language_listening_curriculum.scoring import SCORE_WEIGHTS, score_candidate
from app.services.language_listening_curriculum.skills import (
    neglected_skills,
    parse_weak_listening_skills,
    pick_skill_focus,
    _primary_weak_share,
)
from app.services.language_listening_curriculum.types import (
    CurriculumHistoryEntry,
    CurriculumRecommendation,
    CurriculumTelemetry,
    ObjectiveState,
)
from app.services.language_listening_intelligence.types import ListeningHistoryEntry


def build_curriculum_prompt_block(recommendation: CurriculumRecommendation) -> str:
    skills = ", ".join(recommendation.skill_focus)
    objectives = "; ".join(recommendation.objectives[:2])
    review = ", ".join(recommendation.review_objectives) if recommendation.review_objectives else "none"
    return (
        "[CURRICULUM FOCUS]\n"
        f"Educational stage: {recommendation.curriculum_stage}\n"
        f"Lesson intent: {recommendation.lesson_intent.replace('_', ' ')}\n"
        f"Knowledge progression node: {recommendation.knowledge_node.replace('_', ' ')}\n"
        f"Primary listening skills to practice: {skills}\n"
        f"Learning objectives this lesson supports: {objectives}\n"
        f"Spaced review objectives (if any): {review}\n"
        "Balance skills naturally — do not over-focus a single skill. "
        "Do not change CEFR level or question-type rules.\n"
        "[/CURRICULUM FOCUS]"
    )


def recommend_curriculum_plan(
    level: str,
    intelligence_history: list[ListeningHistoryEntry],
    curriculum_history: list[CurriculumHistoryEntry],
    *,
    themes: str = "",
    topics: str = "",
    weaknesses: list[str] | None = None,
    generation_index: int | None = None,
) -> CurriculumRecommendation:
    """Select the highest-scoring curriculum-aware listening plan."""
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

    candidates = enumerate_intelligence_candidates(
        level,
        intelligence_history,
        themes=themes,
        topics=topics,
        generation_index=gen_idx,
    )

    def _build_recommendation(plan) -> CurriculumRecommendation:
        knowledge_node = knowledge_node_for_situation(plan.situation)
        score = score_candidate(
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
            topics=topics,
            generation_index=gen_idx,
        )
        return CurriculumRecommendation(
            plan=plan,
            skill_focus=skill_focus,
            objectives=objectives,
            knowledge_node=knowledge_node,
            review_objectives=review_objectives,
            score=score,
            curriculum_stage=_curriculum_stage(objective_progress),
            lesson_intent=intent.value,
            selection_reason=(
                f"intent={intent.value} score={score.total:.2f} "
                f"coverage={score.coverage_balance:.2f} weak={score.weak_skill_recovery:.2f} "
                f"review={score.review_priority:.2f}"
            ),
        )

    if not candidates:
        from app.services.language_listening_intelligence import select_next_listening_plan

        plan = select_next_listening_plan(
            level,
            intelligence_history,
            themes=themes,
            topics=topics,
            generation_index=gen_idx,
        )
        rec = _build_recommendation(plan)
        return CurriculumRecommendation(
            plan=rec.plan,
            skill_focus=rec.skill_focus,
            objectives=rec.objectives,
            knowledge_node=rec.knowledge_node,
            review_objectives=rec.review_objectives,
            score=rec.score,
            curriculum_stage="fallback",
            lesson_intent=intent.value,
            selection_reason="no_candidates_fallback",
        )

    best: CurriculumRecommendation | None = None
    for plan in candidates:
        rec = _build_recommendation(plan)
        if best is None or rec.score.total > best.score.total:
            best = rec
    assert best is not None
    return best


def _curriculum_stage(progress: dict) -> str:
    mastered = sum(1 for p in progress.values() if p.state == ObjectiveState.mastered)
    practicing = sum(1 for p in progress.values() if p.state == ObjectiveState.practicing)
    if mastered >= max(3, len(progress) // 4):
        return "consolidating"
    if practicing >= 1:
        return "developing"
    return "exploring"


def compute_curriculum_telemetry(
    curriculum_history: list[CurriculumHistoryEntry],
    *,
    weaknesses: list[str] | None = None,
    level: str = "B1",
    scores: list[float] | None = None,
    contributions: list[dict[str, float]] | None = None,
) -> CurriculumTelemetry:
    skill_counts = Counter()
    for entry in curriculum_history:
        if entry.skill_focus:
            skill_counts[entry.skill_focus[0]] += 1

    total_lessons = len(curriculum_history) or 1
    skill_pct = {k: round(v / total_lessons, 3) for k, v in skill_counts.items()}

    progress = build_objective_progress(curriculum_history, level)
    mastered = [oid for oid, p in progress.items() if p.state == ObjectiveState.mastered]
    under = [oid for oid, p in progress.items() if p.state in (ObjectiveState.introduced, ObjectiveState.practicing)]
    review_queue = [
        oid
        for oid, p in progress.items()
        if p.state == ObjectiveState.mastered
        and len(curriculum_history) - p.last_seen_index >= 12
    ]

    obj_counts = Counter()
    for entry in curriculum_history:
        for oid in entry.objectives:
            obj_counts[oid] += 1
    obj_pct = {k: round(v / total_lessons, 3) for k, v in obj_counts.items()}

    intents = [h.lesson_intent for h in curriculum_history]
    dist = intent_distribution(intents)

    weak_skill_names = {s.value for s in parse_weak_listening_skills(weaknesses)}
    weak_primary = sum(
        1 for h in curriculum_history if h.skill_focus and h.skill_focus[0] in weak_skill_names
    )
    weak_pct = round(weak_primary / total_lessons, 3)

    contrib_avg: dict[str, float] = {}
    if contributions:
        for key in SCORE_WEIGHTS:
            contrib_avg[key] = round(
                sum(c.get(key, 0.0) for c in contributions) / len(contributions),
                4,
            )

    return CurriculumTelemetry(
        current_stage=_curriculum_stage(progress),
        skill_coverage=dict(skill_counts),
        skill_coverage_pct=skill_pct,
        objectives_mastered=mastered,
        objectives_under_practiced=under,
        objective_coverage_pct=obj_pct,
        review_queue=review_queue,
        knowledge_node=curriculum_history[-1].knowledge_node if curriculum_history else "",
        average_recommendation_score=round(sum(scores) / len(scores), 2) if scores else 0.0,
        weak_skills_targeted=[s.value for s in parse_weak_listening_skills(weaknesses)],
        neglected_skills=neglected_skills(level, curriculum_history),
        intent_distribution=dist,
        weak_skill_pct=weak_pct,
        review_pct=dist.get(LessonIntent.review.value, 0.0),
        score_contributions_avg=contrib_avg,
    )
