"""Weighted multi-objective recommendation scoring (Phase 2.3.1)."""

from __future__ import annotations

from app.services.language_listening_curriculum.intent import INTENT_BANDS, LessonIntent
from app.services.language_listening_curriculum.knowledge import KNOWLEDGE_CHAINS, progression_boost
from app.services.language_listening_curriculum.memory import seen_knowledge_nodes
from app.services.language_listening_curriculum.objectives import review_priority_score
from app.services.language_listening_curriculum.skills import ListeningSkillFocus, neglected_skills
from app.services.language_listening_curriculum.types import (
    CurriculumHistoryEntry,
    CurriculumRecommendationScore,
    ObjectiveProgress,
)
from app.services.language_listening_intelligence.memory import (
    recent_categories,
    recent_formats,
    situation_on_cooldown,
)
from app.services.language_listening_intelligence.selector import SITUATION_COOLDOWN
from app.services.language_listening_intelligence.types import ListeningHistoryEntry, ListeningIntelligencePlan

FATIGUE_FORMATS = frozenset({"dialogue", "interview", "discussion"})
FATIGUE_THRESHOLD = 3
FATIGUE_RELIEF_FORMATS = frozenset({"news", "lecture", "podcast", "story", "panel", "announcement", "monologue"})

# Normalized weights — sum to 1.0
SCORE_WEIGHTS: dict[str, float] = {
    "weak_skill": 0.11,
    "coverage_balance": 0.13,
    "curriculum_progression": 0.11,
    "review": 0.10,
    "knowledge_dependency": 0.08,
    "topic_diversity": 0.08,
    "category_diversity": 0.08,
    "interest": 0.05,
    "difficulty_rotation": 0.05,
    "narrative_rotation": 0.06,
    "fatigue": 0.05,
    "cooldown": 0.05,
    "intelligence_base": 0.05,
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _fatigue_relief(plan: ListeningIntelligencePlan, history: list[CurriculumHistoryEntry]) -> float:
    recent = [h.narrative_format for h in history[-FATIGUE_THRESHOLD:]]
    if len(recent) < FATIGUE_THRESHOLD or not all(fmt in FATIGUE_FORMATS for fmt in recent):
        return 1.0
    return 1.0 if plan.narrative_format.value in FATIGUE_RELIEF_FORMATS else 0.35


def _weak_skill_factor(
    weak_skills: tuple[ListeningSkillFocus, ...],
    skill_focus: tuple[str, ...],
    intent: LessonIntent,
    recent_weak_share: float,
) -> float:
    if not weak_skills:
        return 0.5
    weak_in_focus = sum(1 for s in skill_focus if s in {w.value for w in weak_skills})
    if intent == LessonIntent.weak_recovery:
        base = 0.7 + 0.15 * min(1, weak_in_focus)
    elif weak_in_focus:
        base = 0.55 + 0.1 * weak_in_focus
    else:
        base = 0.45
    # Penalize if recent history already over weak-recovery band
    _low, high = INTENT_BANDS[LessonIntent.weak_recovery]
    if recent_weak_share >= high:
        base *= 0.4 if weak_in_focus else 0.85
    return _clamp01(base)


def _coverage_factor(level: str, skill_focus: tuple[str, ...], curriculum_history: list[CurriculumHistoryEntry]) -> float:
    neglected = neglected_skills(level, curriculum_history)
    if not skill_focus:
        return 0.3
    boosts = sum(1 for s in skill_focus if s in neglected)
    return _clamp01(0.45 + 0.25 * boosts + (0.15 if not neglected else 0.0))


def score_candidate(
    plan: ListeningIntelligencePlan,
    *,
    level: str,
    intelligence_history: list[ListeningHistoryEntry],
    curriculum_history: list[CurriculumHistoryEntry],
    objective_progress: dict[str, ObjectiveProgress],
    weak_skills: tuple[ListeningSkillFocus, ...],
    skill_focus: tuple[str, ...],
    objectives: tuple[str, ...],
    intent: LessonIntent,
    recent_intents: list[str],
    themes: str = "",
    topics: str = "",
    generation_index: int = 0,
) -> CurriculumRecommendationScore:
    on_cooldown = situation_on_cooldown(plan.situation.value, intelligence_history, SITUATION_COOLDOWN)

    recent_cats = recent_categories(intelligence_history, 12)
    cat_counts = {c: recent_cats.count(c) for c in set(recent_cats)}
    avg_cat = sum(cat_counts.values()) / max(1, len(cat_counts) or 1)
    category_div = _clamp01(0.4 + max(0, avg_cat - cat_counts.get(plan.category.value, 0)) * 0.15)

    recent_fmts = recent_formats(intelligence_history, 8)
    narrative_rot = 0.35 if plan.narrative_format.value in recent_fmts[-3:] else 1.0

    seen_nodes = seen_knowledge_nodes(curriculum_history)
    curriculum_prog = progression_boost(plan.situation, seen_nodes=seen_nodes, chain=KNOWLEDGE_CHAINS[0])
    curriculum_prog_n = _clamp01((curriculum_prog - 0.5) / 1.3)

    knowledge_dep = _clamp01(curriculum_prog_n)

    window = recent_intents[-40:]
    weak_share = window.count(LessonIntent.weak_recovery.value) / max(1, len(window))
    weak_recovery = _weak_skill_factor(weak_skills, skill_focus, intent, weak_share)

    review = _clamp01(0.35 + review_priority_score(objectives, objective_progress, generation_index) * 0.65)

    coverage = _coverage_factor(level, skill_focus, curriculum_history)

    fatigue = _fatigue_relief(plan, curriculum_history)

    recent_diff = [h.difficulty_band for h in intelligence_history[-3:] if hasattr(h, "difficulty_band")]
    difficulty_rot = 0.65 if recent_diff and plan.difficulty_band.value == recent_diff[-1] else 1.0

    interest = 0.55 if topics else 0.45
    topic_div = 0.0 if on_cooldown else 1.0
    cooldown = 0.0 if on_cooldown else 1.0
    cefr = 1.0
    intel_base = _clamp01(plan.selection_score / 3.0)

    intent_fit = 0.5
    if intent == LessonIntent.exploration and plan.narrative_format.value in {"podcast", "lecture", "story", "news"}:
        intent_fit = 0.85
    elif intent == LessonIntent.review:
        intent_fit = 0.75
    elif intent == LessonIntent.weak_recovery and weak_skills:
        intent_fit = 0.7
    elif intent == LessonIntent.balanced_coverage:
        intent_fit = 0.65

    components = {
        "weak_skill": weak_recovery,
        "coverage_balance": coverage,
        "curriculum_progression": curriculum_prog_n,
        "review": review,
        "knowledge_dependency": knowledge_dep,
        "topic_diversity": topic_div,
        "category_diversity": category_div,
        "interest": interest,
        "difficulty_rotation": difficulty_rot,
        "narrative_rotation": narrative_rot,
        "fatigue": fatigue,
        "cooldown": cooldown,
        "intelligence_base": intel_base,
    }

    total = sum(SCORE_WEIGHTS[k] * components[k] for k in SCORE_WEIGHTS) * (0.95 + 0.05 * intent_fit)

    contributions = {k: round(SCORE_WEIGHTS[k] * components[k], 4) for k in SCORE_WEIGHTS}

    return CurriculumRecommendationScore(
        total=round(total, 4),
        cefr_suitability=cefr,
        curriculum_progression=curriculum_prog_n,
        weak_skill_recovery=weak_recovery,
        review_priority=review,
        topic_diversity=topic_div,
        category_diversity=category_div,
        interest_weight=interest,
        difficulty_rotation=difficulty_rot,
        narrative_rotation=narrative_rot,
        cooldown=cooldown,
        intelligence_base=intel_base,
        fatigue_relief=fatigue,
        coverage_balance=coverage,
        knowledge_dependency=knowledge_dep,
        intent_fit=intent_fit,
        contributions=contributions,
    )
