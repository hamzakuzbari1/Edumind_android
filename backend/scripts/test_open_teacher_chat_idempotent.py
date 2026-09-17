"""Call open_course_teacher_conversation 10x; must return same thread_id."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.test_users import default_test_email
from app.db.session import AsyncSessionLocal
from app.models.conversation import ConversationThread
from app.models.user import User
from app.services.messaging_service import open_course_teacher_conversation


async def main() -> None:
    test_email = default_test_email("auth_student")
    async with AsyncSessionLocal() as db:
        student = await db.scalar(select(User).where(User.email == test_email))
        if not student:
            print(f"No test student at {test_email}. Run: python scripts/seed_test_users.py")
            return

        thread = await db.scalar(
            select(ConversationThread).where(
                ConversationThread.student_id == student.id,
            ).limit(1)
        )
        course_id = thread.course_id if thread else 22

        ids: list[int] = []
        for i in range(10):
            out = await open_course_teacher_conversation(db, student, course_id, include_parent=False)
            await db.commit()
            ids.append(out.thread_id)
            print(f"call {i + 1}: thread_id={out.thread_id} created={out.created}")

        unique = set(ids)
        print(f"unique thread ids: {unique}")
        print("PASS" if len(unique) == 1 else "FAIL")


if __name__ == "__main__":
    asyncio.run(main())
