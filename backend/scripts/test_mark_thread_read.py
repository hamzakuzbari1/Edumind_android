"""Verify mark_thread_read persists last_read_at across sessions."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.conversation import ConversationParticipant, ConversationThread
from app.models.user import User, UserRole
from app.services.messaging_service import get_conversation, list_conversations, mark_thread_read


async def main() -> None:
    async with AsyncSessionLocal() as db:
        student = await db.scalar(
            select(User).where(User.role == UserRole.student).order_by(User.id).limit(1)
        )
        if not student:
            print("no student")
            return
        part = await db.scalar(
            select(ConversationParticipant).where(
                ConversationParticipant.user_id == student.id
            )
        )
        if not part:
            print("no thread for student")
            return
        thread_id = part.thread_id

        before = await list_conversations(db, student)
        row = next((c for c in before.conversations if c.id == thread_id), None)
        print(f"before unread: {row.unread_count if row else 'n/a'}")

        await get_conversation(db, student, thread_id, mark_read=True)

    async with AsyncSessionLocal() as db2:
        student = await db2.scalar(select(User).where(User.id == student.id))
        after = await list_conversations(db2, student)
        row2 = next((c for c in after.conversations if c.id == thread_id), None)
        print(f"after unread (new session): {row2.unread_count if row2 else 'n/a'}")

        detail = await get_conversation(db2, student, thread_id, mark_read=False)
        print(f"detail unread: {detail.unread_count}")
        ok = row2 is not None and row2.unread_count == 0
        print("PASS" if ok else "FAIL")


if __name__ == "__main__":
    asyncio.run(main())
