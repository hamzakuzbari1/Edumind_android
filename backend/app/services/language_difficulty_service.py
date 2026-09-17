"""Phase 3 — Adaptive Difficulty Engine.

Goes beyond a single CEFR level: a fine-grained per-dimension difficulty modifier derived from the
unified learner model (`ComponentMastery`). REUSES existing data — NO new tables. Produces a
`DifficultyProfile` (per-skill/-category modifiers + an `effective_level` like "B1+"/"B1-"/"A2+" and
a recommended content complexity) that content selection and lesson generation can read.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.learner_model import ComponentMastery, KnowledgeComponent
from app.services.language_cache import TTLCache
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR
from app.models.language.enums import LanguageLevel

# Dimensions reported in the profile (grounded in existing data): the 4 display skills + the two
# main knowledge-component categories.
SKILL_DIMS = ("reading", "listening", "writing", "speaking")
CATEGORY_DIMS = ("grammar", "vocabulary")
ALL_DIMS = CATEGORY_DIMS + SKILL_DIMS

# The profile aggregates mastery and changes slowly; cache briefly to spare the hot path (adaptive
# generation / daily mission / coach) two aggregation queries per call.
_PROFILE_CACHE = TTLCache()
_PROFILE_TTL = 60.0


# --------------------------------------------------------------------------------------------------
# Pure helpers (no I/O — unit-tested directly)
# --------------------------------------------------------------------------------------------------
def modifier_from_score(score: float | None) -> float:
    """Map a 0-100 mastery score to a difficulty modifier in [-1.0, +0.5]. None (no data) = neutral."""
    if score is None:
        return 0.0
    if score > 85:
        return 0.5
    if score >= 70:
        return 0.0
    if score >= 55:
        return -0.5
    return -1.0


def weighted_average(modifiers: dict[str, float]) -> float:
    """Equal-weight mean of the provided modifiers (empty -> 0.0)."""
    if not modifiers:
        return 0.0
    return sum(modifiers.values()) / len(modifiers)


def effective_label(base_level: str, avg_mod: float) -> str:
    """Combine a base CEFR level with an average modifier into a sub-level label.

    +0.5 -> "{base}+", -0.5 -> "{base}-", -1.0 -> "{base-1}+" (e.g. B1 -> A2+). Clamped at A1/C2.
    """
    try:
        base = LanguageLevel(base_level)
    except ValueError:
        base = LanguageLevel.A1
    rank = CEFR_RANK[base]
    if avg_mod >= 0.25:
        return base.value if rank >= 6 else f"{base.value}+"
    if avg_mod <= -0.75:
        lower = max(1, rank - 1)
        lbl = RANK_CEFR[lower].value
        return f"{lbl}+" if lower < 6 else lbl
    if avg_mod <= -0.25:
        return f"{base.value}-"
    return base.value


def recommended_complexity(base_level: str, avg_mod: float) -> str:
    """Coarse content-complexity band from the effective numeric level."""
    try:
        rank = CEFR_RANK[LanguageLevel(base_level)]
    except ValueError:
        rank = 1
    val = rank + avg_mod
    if val < 2.5:
        return "simple"
    if val < 3.5:
        return "moderate"
    if val < 5.5:
        return "complex"
    return "advanced"


# --------------------------------------------------------------------------------------------------
# Data aggregation
# --------------------------------------------------------------------------------------------------
async def _base_level(db: AsyncSession, *, student_id: int, language_id: int) -> str:
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics and analytics.overall_level_internal:
        return analytics.overall_level_internal.value
    return LanguageLevel.A1.value


async def _skill_scores(db: AsyncSession, *, student_id: int, language_id: int) -> dict[str, float]:
    """Mean mastery (0-100) per display skill, over components with real evidence."""
    rows = (
        await db.execute(
            select(KnowledgeComponent.display_skill, func.avg(ComponentMastery.p_mastery))
            .join(ComponentMastery, ComponentMastery.component_id == KnowledgeComponent.id)
            .where(
                ComponentMastery.student_id == student_id,
                ComponentMastery.language_id == language_id,
                ComponentMastery.evidence_count > 0,
            )
            .group_by(KnowledgeComponent.display_skill)
        )
    ).all()
    out: dict[str, float] = {}
    for skill, avg in rows:
        if avg is None:
            continue
        key = skill.value if hasattr(skill, "value") else str(skill)
        out[key] = round(float(avg) * 100, 1)
    return out


async def _category_scores(db: AsyncSession, *, student_id: int, language_id: int) -> dict[str, float]:
    """Mean mastery (0-100) per knowledge-component category (grammar/vocabulary/…)."""
    rows = (
        await db.execute(
            select(KnowledgeComponent.category, func.avg(ComponentMastery.p_mastery))
            .join(ComponentMastery, ComponentMastery.component_id == KnowledgeComponent.id)
            .where(
                ComponentMastery.student_id == student_id,
                ComponentMastery.language_id == language_id,
                ComponentMastery.evidence_count > 0,
            )
            .group_by(KnowledgeComponent.category)
        )
    ).all()
    out: dict[str, float] = {}
    for category, avg in rows:
        if avg is None or not category:
            continue
        out[str(category).lower()] = round(float(avg) * 100, 1)
    return out


async def calculate_modifier(
    db: AsyncSession, *, student_id: int, language_id: int, use_cache: bool = True
) -> dict:
    """Full DifficultyProfile: per-dimension modifiers + effective level + recommended complexity.

    Cached for a short TTL (mastery aggregates change slowly); pass use_cache=False to force a fresh
    computation right after writing new evidence.
    """
    cache_key = (student_id, language_id)
    if use_cache:
        cached = _PROFILE_CACHE.get(cache_key)
        if cached is not None:
            return cached

    base_level = await _base_level(db, student_id=student_id, language_id=language_id)
    skill_scores = await _skill_scores(db, student_id=student_id, language_id=language_id)
    category_scores = await _category_scores(db, student_id=student_id, language_id=language_id)
    scores = {**{d: skill_scores.get(d) for d in SKILL_DIMS}, **{d: category_scores.get(d) for d in CATEGORY_DIMS}}

    modifiers = {dim: modifier_from_score(scores.get(dim)) for dim in ALL_DIMS}
    # Average only over dimensions that actually have evidence (don't dilute with neutral no-data dims).
    present = {dim: modifiers[dim] for dim in ALL_DIMS if scores.get(dim) is not None}
    avg_mod = weighted_average(present)

    result = {
        "cefr_level": base_level,
        "modifiers": modifiers,
        "scores": {dim: scores.get(dim) for dim in ALL_DIMS},
        "effective_level": effective_label(base_level, avg_mod),
        "recommended_complexity": recommended_complexity(base_level, avg_mod),
        "average_modifier": round(avg_mod, 3),
    }
    _PROFILE_CACHE.set(cache_key, result, _PROFILE_TTL)
    return result


async def get_lesson_difficulty(
    db: AsyncSession, *, student_id: int, language_id: int, skill: str
) -> str:
    """Effective sub-level label for one skill — for adaptive content selection."""
    base_level = await _base_level(db, student_id=student_id, language_id=language_id)
    skill = (skill or "").lower()
    if skill in SKILL_DIMS:
        score = (await _skill_scores(db, student_id=student_id, language_id=language_id)).get(skill)
    else:
        score = (await _category_scores(db, student_id=student_id, language_id=language_id)).get(skill)
    return effective_label(base_level, modifier_from_score(score))
