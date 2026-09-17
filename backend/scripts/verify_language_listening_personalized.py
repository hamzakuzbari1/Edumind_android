"""Verify Phase 2 personalized listening: pool, timings, cross-student isolation."""

from __future__ import annotations

import asyncio
import time

from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageSkill
from app.services.claude_service import is_claude_configured
from app.services.language_listening_service import (
    _adaptive_level,
    _unseen_personalized_count,
    next_listening,
)
from app.services.language_subscription_service import get_default_language

STUDENT_A = 75
STUDENT_B = 77


async def pool_snapshot(db, student_id: int) -> tuple[str, int, int]:
    language = await get_default_language(db)
    level = await _adaptive_level(db, student_id=student_id, language_id=language.id)
    unseen = await _unseen_personalized_count(
        db, student_id=student_id, language_id=language.id, level=level
    )
    total = (
        await db.execute(
            select(func.count())
            .select_from(LanguageContentItem)
            .where(
                LanguageContentItem.student_id == student_id,
                LanguageContentItem.skill == LanguageSkill.listening,
            )
        )
    ).scalar()
    return level, unseen, int(total or 0)


async def titles_for_student(db, student_id: int) -> list[tuple[str, str]]:
    rows = (
        await db.execute(
            select(LanguageContentItem.title, LanguageContentItem.body_json)
            .where(
                LanguageContentItem.student_id == student_id,
                LanguageContentItem.skill == LanguageSkill.listening,
            )
            .order_by(LanguageContentItem.id)
        )
    ).all()
    return [(t, (b or {}).get("audio_transcript", "")[:80]) for t, b in rows]


async def main() -> None:
    print("Claude configured:", is_claude_configured())

    async with AsyncSessionLocal() as db:
        for sid in (STUDENT_A, STUDENT_B):
            lvl, unseen, total = await pool_snapshot(db, sid)
            print(f"Student {sid} before: level={lvl} unseen={unseen} total_personalized={total}")

    t0 = time.perf_counter()
    async with AsyncSessionLocal() as db:
        lesson_a1 = await next_listening(db, student_id=STUDENT_A)
    t_gen = time.perf_counter() - t0
    print(f"Student A first next_listening: {t_gen:.2f}s")
    print(f"  title={lesson_a1.get('title') if lesson_a1 else None}")

    t0 = time.perf_counter()
    async with AsyncSessionLocal() as db:
        lesson_a2 = await next_listening(db, student_id=STUDENT_A)
    t_serve = time.perf_counter() - t0
    print(f"Student A second next_listening: {t_serve:.2f}s")
    print(f"  title={lesson_a2.get('title') if lesson_a2 else None}")

    async with AsyncSessionLocal() as db:
        _, unseen, total = await pool_snapshot(db, STUDENT_A)
        print(f"Student A after: unseen={unseen} total_personalized={total}")

    t0 = time.perf_counter()
    async with AsyncSessionLocal() as db:
        lesson_b1 = await next_listening(db, student_id=STUDENT_B)
    t_b = time.perf_counter() - t0
    print(f"Student B first next_listening: {t_b:.2f}s")
    print(f"  title={lesson_b1.get('title') if lesson_b1 else None}")

    async with AsyncSessionLocal() as db:
        titles_a = await titles_for_student(db, STUDENT_A)
        titles_b = await titles_for_student(db, STUDENT_B)
        overlap = {t for t, _ in titles_a} & {t for t, _ in titles_b}
        print("Student A lessons:", titles_a)
        print("Student B lessons:", titles_b)
        print("Title overlap:", overlap)
        different = bool(
            lesson_a1 and lesson_b1 and lesson_a1["title"] != lesson_b1["title"]
        )
        print("Different first lessons:", different)
        print("Second request faster than first:", t_serve < t_gen)
        print("Batch generated for A:", total)


if __name__ == "__main__":
    asyncio.run(main())
