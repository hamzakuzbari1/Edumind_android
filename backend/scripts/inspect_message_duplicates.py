"""Inspect duplicate messaging threads. Run: python -m scripts.inspect_message_duplicates"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal
from app.models.catalog import TeacherProfile
from app.models.conversation import ConversationParticipant, ConversationParticipantRole, ConversationThread
from app.models.user import User


async def main() -> None:
    async with AsyncSessionLocal() as db:
        threads = (
            await db.execute(
                select(ConversationThread).order_by(
                    ConversationThread.student_id,
                    ConversationThread.course_id.nulls_first(),
                    ConversationThread.id,
                )
            )
        ).scalars().all()

        rows = []
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
            msg_count = await db.scalar(
                text("SELECT COUNT(*) FROM conversation_messages WHERE thread_id = :tid"),
                {"tid": t.id},
            )
            rows.append(
                {
                    "thread_id": t.id,
                    "title": t.title,
                    "student_id": t.student_id,
                    "course_id": t.course_id,
                    "teacher_user_ids": teacher_ids,
                    "participant_ids": [p.user_id for p in parts],
                    "thread_type": str(t.thread_type),
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "last_message_at": t.last_message_at.isoformat() if t.last_message_at else None,
                    "message_count": int(msg_count or 0),
                }
            )

        # Groups: (teacher_id, student_id, course_id) — course_id None is distinct bucket
        by_key: dict[tuple, list] = defaultdict(list)
        for r in rows:
            for tid in r["teacher_user_ids"] or [None]:
                key = (tid, r["student_id"], r["course_id"])
                by_key[key].append(r)

        dupes = {k: v for k, v in by_key.items() if len(v) > 1}

        # Teachers named like ياسر
        teachers = (
            await db.execute(
                select(TeacherProfile, User)
                .join(User, User.id == TeacherProfile.user_id)
                .where(TeacherProfile.full_name.ilike("%ياسر%"))
            )
        ).all()

        print("=== Teachers matching ياسر ===")
        for tp, u in teachers:
            print(f"  user_id={u.id} profile_id={tp.id} name={tp.full_name}")

        print(f"\n=== Total threads: {len(rows)} ===")
        print(f"=== Duplicate groups (teacher, student, course): {len(dupes)} ===\n")

        for key, group in sorted(dupes.items(), key=lambda x: (x[0][1], x[0][0] or 0)):
            print(f"KEY teacher={key[0]} student={key[1]} course={key[2]}")
            for g in group:
                print(f"  thread={g['thread_id']} msgs={g['message_count']} title={g['title']!r} created={g['created_at']}")
            print()

        print("=== ALL threads (summary) ===")
        print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
