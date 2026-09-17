"""Read-only parent↔teacher thread lookup for catalog pages (no enrollment gates)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationThread, ConversationThreadType
from app.services.messaging_service import (
    _get_participant,
    _thread_message_count,
    _thread_rank_key,
    _unread_for_participant,
)


async def find_parent_teacher_thread(
    db: AsyncSession,
    *,
    parent_id: int,
    teacher_id: int,
    student_id: int,
    course_id: int,
) -> ConversationThread | None:
    """Dedicated parent↔teacher thread only — never student↔teacher threads."""
    result = await db.execute(
        select(ConversationThread).where(
            ConversationThread.thread_type == ConversationThreadType.teacher_parent,
            ConversationThread.parent_user_id == parent_id,
            ConversationThread.teacher_user_id == teacher_id,
            ConversationThread.course_id == course_id,
        )
    )
    candidates = list(result.scalars().all())
    if not candidates:
        return None
    counts = {t.id: await _thread_message_count(db, t.id) for t in candidates}
    return max(candidates, key=lambda t: _thread_rank_key(t, counts[t.id]))


async def thread_state_for_parent(
    db: AsyncSession, parent_id: int, thread: ConversationThread | None
) -> tuple[int | None, str | None, str | None, int]:
    if not thread:
        return None, None, None, 0
    part = await _get_participant(db, thread.id, parent_id)
    if not part:
        return thread.id, thread.last_message_preview, (
            thread.last_message_at.isoformat() if thread.last_message_at else None
        ), 0
    unread = await _unread_for_participant(db, thread.id, part)
    return (
        thread.id,
        thread.last_message_preview,
        thread.last_message_at.isoformat() if thread.last_message_at else None,
        unread,
    )
