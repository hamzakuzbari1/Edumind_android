from __future__ import annotations

import math
from collections import Counter

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.path import LanguageLearningPath, LanguagePathItem

LEVEL_ORDER = [LanguageLevel.A1, LanguageLevel.A2, LanguageLevel.B1, LanguageLevel.B2, LanguageLevel.C1, LanguageLevel.C2]


def _level_rank(level: LanguageLevel | None) -> int:
    if not level:
        return 0
    try:
        return LEVEL_ORDER.index(level)
    except Exception:
        return 0


def _weighted_skill_plan(levels: dict[LanguageSkill, LanguageLevel], total_items: int = 20) -> list[LanguageSkill]:
    # Sort skills by ascending level (weakest -> strongest)
    ordered = sorted(levels.items(), key=lambda kv: (_level_rank(kv[1]), kv[0].value))
    skills = [kv[0] for kv in ordered]
    if len(skills) != 4:
        # fallback deterministic order
        skills = [LanguageSkill.reading, LanguageSkill.listening, LanguageSkill.writing, LanguageSkill.speaking]

    # 40/30/20/10 distribution across (weakest, second, third, strongest)
    weights = [0.40, 0.30, 0.20, 0.10]
    counts = [int(math.floor(total_items * w)) for w in weights]
    while sum(counts) < total_items:
        # distribute remainder to weakest first
        for i in range(4):
            counts[i] += 1
            if sum(counts) >= total_items:
                break

    plan: list[LanguageSkill] = []
    for skill, c in zip(skills, counts, strict=False):
        plan.extend([skill] * int(c))
    return plan[:total_items]


async def generate_learning_path(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    assessment_id: int | None,
    overall_level: LanguageLevel | None,
    skill_levels: dict[LanguageSkill, LanguageLevel],
    total_items: int = 20,
) -> LanguageLearningPath:
    # One active path at a time per student/language: replace existing.
    existing = await db.execute(
        select(LanguageLearningPath).where(
            LanguageLearningPath.student_id == student_id,
            LanguageLearningPath.language_id == language_id,
        )
    )
    prev = existing.scalar_one_or_none()
    if prev:
        await db.execute(delete(LanguagePathItem).where(LanguagePathItem.path_id == prev.id))
        await db.execute(delete(LanguageLearningPath).where(LanguageLearningPath.id == prev.id))
        await db.flush()

    path = LanguageLearningPath(
        student_id=student_id,
        language_id=language_id,
        assessment_id=assessment_id,
        overall_level=overall_level,
        path_json={
            "version": "phase_b_v1",
            "distribution": {"weakest": 0.4, "second": 0.3, "third": 0.2, "strongest": 0.1},
            "skill_levels": {k.value: v.value for k, v in skill_levels.items()},
            "total_items": total_items,
        },
    )
    db.add(path)
    await db.flush()

    plan = _weighted_skill_plan(skill_levels, total_items=total_items)
    counts = Counter(plan)
    path.path_json["counts"] = {k.value: int(v) for k, v in counts.items()}

    # For Phase B: create path items with (skill, level) and no content linking yet.
    for idx, skill in enumerate(plan):
        db.add(
            LanguagePathItem(
                path_id=path.id,
                skill=skill,
                level=skill_levels.get(skill) or (overall_level or LanguageLevel.A1),
                content_item_id=None,
                sort_order=idx,
            )
        )

    # Update analytics focus/strength as a hint for UI.
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics:
        ordered = sorted(skill_levels.items(), key=lambda kv: (_level_rank(kv[1]), kv[0].value))
        analytics.primary_focus_skill = ordered[0][0].value if ordered else None
        analytics.strength_skill = ordered[-1][0].value if ordered else None

    return path
