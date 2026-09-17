"""Merge duplicate messaging threads in DB. Run: python -m scripts.cleanup_message_duplicates"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.conversation import ConversationParticipant, ConversationParticipantRole, ConversationThread
from app.services.messaging_service import _reconcile_course_teacher_threads


async def main() -> None:
    async with AsyncSessionLocal() as db:
        threads = (await db.execute(select(ConversationThread))).scalars().all()
        scopes: set[tuple[int, int, int]] = set()
        for t in threads:
            parts = (
                await db.execute(
                    select(ConversationParticipant).where(
                        ConversationParticipant.thread_id == t.id
                    )
                )
            ).scalars().all()
            teacher_ids = [
                p.user_id
                for p in parts
                if (
                    p.role
                    if isinstance(p.role, ConversationParticipantRole)
                    else ConversationParticipantRole(p.role)
                )
                == ConversationParticipantRole.teacher
            ]
            if not teacher_ids:
                continue
            tid = teacher_ids[0]
            if t.course_id:
                scopes.add((tid, t.student_id, t.course_id))
            else:
                for other in threads:
                    if other.student_id == t.student_id and other.course_id:
                        scopes.add((tid, t.student_id, other.course_id))

        for teacher_id, student_id, course_id in sorted(scopes):
            await _reconcile_course_teacher_threads(
                db,
                course_id=course_id,
                student_id=student_id,
                teacher_id=teacher_id,
                parent_ids=[],
            )
        await db.commit()
        print(f"Reconciled {len(scopes)} teacher/student/course scopes.")


if __name__ == "__main__":
    asyncio.run(main())
