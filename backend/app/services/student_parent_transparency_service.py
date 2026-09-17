"""Student-facing view of linked parent accounts (read-only)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.parent_link import ParentStudentLink
from app.models.user import User
from app.schemas.student_parent import (
    LinkedParentOut,
    LinkedParentsSummaryOut,
    StudentLinkedParentsOut,
)

ACTIVE_VIEW_WINDOW_DAYS = 30


def _iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _is_active_link(last_viewed_at: datetime | None) -> bool:
    if last_viewed_at is None:
        return True
    if last_viewed_at.tzinfo is None:
        last_viewed_at = last_viewed_at.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(days=ACTIVE_VIEW_WINDOW_DAYS)
    return last_viewed_at >= cutoff


async def list_linked_parents_for_student(db: AsyncSession, student_id: int) -> StudentLinkedParentsOut:
    result = await db.execute(
        select(ParentStudentLink, User)
        .join(User, User.id == ParentStudentLink.parent_id)
        .where(ParentStudentLink.student_id == student_id)
        .order_by(ParentStudentLink.created_at.desc())
    )
    parents: list[LinkedParentOut] = []
    active_count = 0
    for link, parent_user in result.all():
        active = _is_active_link(link.last_viewed_at)
        if active:
            active_count += 1
        parents.append(
            LinkedParentOut(
                parent_id=parent_user.id,
                display_name=parent_user.name,
                relationship_label=link.relationship_label or "parent",
                linked_at=_iso(link.created_at),
                last_viewed_at=_iso(link.last_viewed_at),
                is_active=active,
            )
        )
    return StudentLinkedParentsOut(
        parents=parents,
        summary=LinkedParentsSummaryOut(
            total_linked=len(parents),
            active_linked=active_count,
        ),
    )
