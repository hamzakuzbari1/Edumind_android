"""Async curriculum history loader (Phase 2.3)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.services.language_listening_curriculum.memory import extract_curriculum_history
from app.services.language_listening_curriculum.types import CurriculumHistoryEntry


async def load_curriculum_history(
    db: AsyncSession,
    *,
    language_id: int,
    level: str,
    student_id: int | None = None,
    limit: int = 200,
) -> list[CurriculumHistoryEntry]:
    q = (
        select(LanguageContentItem.body_json)
        .where(
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.skill == LanguageSkill.listening,
            LanguageContentItem.level == LanguageLevel(level),
            LanguageContentItem.is_published.is_(True),
        )
        .order_by(LanguageContentItem.id.desc())
        .limit(limit)
    )
    if hasattr(LanguageContentItem, "student_id") and student_id is not None:
        q = q.where(LanguageContentItem.student_id == student_id)
    elif hasattr(LanguageContentItem, "student_id"):
        q = q.where(LanguageContentItem.student_id.is_(None))

    rows = await db.execute(q)
    bodies = [row[0] for row in rows.all() if isinstance(row[0], dict)]
    bodies.reverse()
    return extract_curriculum_history(bodies)
