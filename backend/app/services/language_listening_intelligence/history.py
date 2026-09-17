"""Load listening intelligence history from stored content (Phase 2.2)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.services.language_listening_intelligence.memory import (
    HISTORY_KEY,
    extract_history_from_bodies,
    history_entry_from_metadata,
)
from app.services.language_listening_intelligence.types import ListeningHistoryEntry


async def load_listening_intelligence_history(
    db: AsyncSession,
    *,
    language_id: int,
    level: str,
    student_id: int | None = None,
    limit: int = 100,
) -> list[ListeningHistoryEntry]:
    """Load chronological history from ``body_json.listening_intelligence`` on stored lessons."""
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
    return extract_history_from_bodies(bodies)


def intelligence_metadata_from_body(body: dict) -> dict | None:
    meta = body.get(HISTORY_KEY)
    return meta if isinstance(meta, dict) else None
