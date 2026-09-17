"""Goal alignment scoring for listening recommendations (Phase 3.1)."""

from __future__ import annotations

from app.services.language_learning_goal.types import GoalAlignmentScore, LearningGoalProfile
from app.services.language_listening_curriculum.knowledge import (
    KNOWLEDGE_CHAINS,
    knowledge_node_for_situation,
    progression_boost,
)
from app.services.language_listening_curriculum.memory import seen_knowledge_nodes
from app.services.language_listening_curriculum.types import CurriculumHistoryEntry
from app.services.language_listening_intelligence.types import DifficultyBand, ListeningIntelligencePlan

GOAL_WEIGHTS: dict[str, float] = {
    "situation": 0.22,
    "format": 0.14,
    "objective": 0.14,
    "category": 0.12,
    "pace": 0.10,
    "narrative": 0.10,
    "difficulty": 0.08,
    "knowledge": 0.10,
}

DEFAULT_GOAL_INFLUENCE = 0.15


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _membership_score(value: str, preferred: frozenset[str]) -> float:
    if not preferred:
        return 0.55
    if value in preferred:
        return 1.0
    return 0.35


def _objective_fit(selected: tuple[str, ...], profile: LearningGoalProfile) -> float:
    if not profile.preferred_objectives:
        return 0.55
    if not selected:
        return 0.4
    overlap = sum(1 for oid in selected if oid in profile.preferred_objectives)
    return _clamp01(0.35 + overlap / max(1, len(profile.preferred_objectives)) * 0.65)


def _difficulty_fit(
    band: DifficultyBand,
    profile: LearningGoalProfile,
    intelligence_history: list,
) -> float:
    recent = [h.difficulty_band for h in intelligence_history[-6:] if getattr(h, "difficulty_band", None)]
    mode = profile.difficulty_progression
    if mode == "gradual":
        if band == DifficultyBand.easy:
            return 0.95
        if band == DifficultyBand.normal:
            return 0.75 if recent.count("easy") >= 2 else 0.55
        return 0.45 if recent.count("normal") >= 2 else 0.35
    if mode == "exam_rigorous":
        if band == DifficultyBand.challenging:
            return 0.95
        if band == DifficultyBand.normal:
            return 0.8
        return 0.5
    if mode == "gradual_to_challenging":
        if band == DifficultyBand.normal:
            return 0.85
        if band == DifficultyBand.challenging and len(intelligence_history) >= 8:
            return 0.9
        if band == DifficultyBand.easy and len(intelligence_history) < 8:
            return 0.8
        return 0.6
    if band == DifficultyBand.normal:
        return 0.85
    return 0.7


def _knowledge_fit(
    plan: ListeningIntelligencePlan,
    profile: LearningGoalProfile,
    curriculum_history: list[CurriculumHistoryEntry],
) -> float:
    if profile.knowledge_chain_preference == "travel_airport":
        chain = KNOWLEDGE_CHAINS[0]
        seen = seen_knowledge_nodes(curriculum_history)
        boost = progression_boost(plan.situation, seen_nodes=seen, chain=chain)
        return _clamp01((boost - 0.5) / 1.3)
    if profile.knowledge_chain_preference in {"academic_progression", "workplace_progression"}:
        preferred = profile.preferred_situations
        if plan.situation.value in preferred:
            return 0.85
        return 0.5
    node = knowledge_node_for_situation(plan.situation)
    if node in profile.preferred_situations:
        return 0.9
    return 0.55


def score_goal_alignment(
    plan: ListeningIntelligencePlan,
    profile: LearningGoalProfile,
    *,
    selected_objectives: tuple[str, ...] = (),
    curriculum_history: list[CurriculumHistoryEntry] | None = None,
    intelligence_history: list | None = None,
) -> GoalAlignmentScore:
    history = curriculum_history or []
    intel = intelligence_history or []
    situation_fit = _membership_score(plan.situation.value, profile.preferred_situations)
    format_fit = max(
        _membership_score(plan.narrative_format.value, profile.preferred_narrative_formats),
        _membership_score(plan.format_hint.value, profile.preferred_format_hints),
    )
    objective_fit = _objective_fit(selected_objectives, profile)
    vocabulary_fit = _membership_score(plan.category.value, profile.preferred_categories)
    pace_fit = _membership_score(plan.pace.value, profile.preferred_pace)
    narrative_fit = _membership_score(plan.narrative_arc.value, profile.preferred_narrative_styles)
    category_fit = vocabulary_fit
    difficulty_fit = _difficulty_fit(plan.difficulty_band, profile, intel)
    knowledge_fit = _knowledge_fit(plan, profile, history)

    components = {
        "situation": situation_fit,
        "format": format_fit,
        "objective": objective_fit,
        "category": category_fit,
        "pace": pace_fit,
        "narrative": narrative_fit,
        "difficulty": difficulty_fit,
        "knowledge": knowledge_fit,
    }
    total = sum(GOAL_WEIGHTS[k] * components[k] for k in GOAL_WEIGHTS)
    contributions = {k: round(GOAL_WEIGHTS[k] * components[k], 4) for k in GOAL_WEIGHTS}

    return GoalAlignmentScore(
        total=round(total, 4),
        situation_fit=round(situation_fit, 4),
        format_fit=round(format_fit, 4),
        objective_fit=round(objective_fit, 4),
        vocabulary_fit=round(vocabulary_fit, 4),
        pace_fit=round(pace_fit, 4),
        narrative_fit=round(narrative_fit, 4),
        category_fit=round(category_fit, 4),
        difficulty_fit=round(difficulty_fit, 4),
        knowledge_fit=round(knowledge_fit, 4),
        contributions=contributions,
    )


def blend_scores(
    curriculum_total: float,
    goal_total: float,
    *,
    goal_influence: float = DEFAULT_GOAL_INFLUENCE,
) -> float:
    influence = max(0.10, min(0.20, goal_influence))
    return round((1.0 - influence) * curriculum_total + influence * goal_total, 4)
