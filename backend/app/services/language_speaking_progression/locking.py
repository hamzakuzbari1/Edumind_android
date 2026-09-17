"""Row lock for speaking progression mutations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.progression import LanguageProgression


async def lock_speaking_progression_row(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LanguageProgression | None:
    result = await db.execute(
        select(LanguageProgression)
        .where(
            LanguageProgression.student_id == student_id,
            LanguageProgression.language_id == language_id,
        )
        .with_for_update()
    )
    return result.scalar_one_or_none()
