"""Verify Phase 8.2 grammar lessons module — curated content, routes, list/detail."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PASS = 0
FAIL = 0


def ok(label: str) -> None:
    global PASS
    PASS += 1
    print(f"OK  {label}")


def fail(label: str, detail: str = "") -> None:
    global FAIL
    FAIL += 1
    msg = f"FAIL {label}"
    if detail:
        msg += f": {detail}"
    print(msg)


def test_curated_levels() -> None:
    from app.services.language_lessons_service import CURATED_LESSONS, LEVELS, TYPES

    if set(LEVELS) == {"A1", "A2", "B1", "B2", "C1", "C2"}:
        ok("CEFR levels A1-C2")
    else:
        fail("LEVELS", str(LEVELS))

    for level in LEVELS:
        items = CURATED_LESSONS.get(level, [])
        grammar = [x for x in items if x.get("type") == "grammar"]
        vocab = [x for x in items if x.get("type") == "vocabulary"]
        if len(grammar) >= 3 and len(vocab) >= 2:
            ok(f"{level}: {len(grammar)} grammar + {len(vocab)} vocabulary lessons")
        else:
            fail(f"{level} lesson mix", f"grammar={len(grammar)} vocab={len(vocab)}")

    if TYPES == ("grammar", "vocabulary"):
        ok("lesson types grammar + vocabulary")
    else:
        fail("TYPES", str(TYPES))


def test_stable_ids() -> None:
    from app.services.language_lessons_service import _curated

    lessons = _curated("A1")
    ids = [l["id"] for l in lessons]
    if ids == ["A1-grammar-1", "A1-grammar-2", "A1-grammar-3", "A1-vocabulary-1", "A1-vocabulary-2"]:
        ok("stable lesson ids for A1")
    else:
        fail("stable ids", str(ids))


def test_routes_registered() -> None:
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    for p in ("/api/student/languages/lessons",):
        if p in paths:
            ok(f"route registered {p}")
        else:
            fail(f"route missing {p}")


async def test_list_and_detail() -> None:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.enrollment import PaymentStatus
    from app.models.language.subscription import LanguageSubscription
    from app.services.language_lessons_service import get_lesson, list_lessons

    async with AsyncSessionLocal() as db:
        student_id = (
            await db.execute(
                select(LanguageSubscription.student_id)
                .where(LanguageSubscription.payment_status == PaymentStatus.paid)
                .limit(1)
            )
        ).scalar_one_or_none()
        if not student_id:
            ok("list/detail skipped (no paid subscriber)")
            return

        payload = await list_lessons(db, student_id=student_id)
        lessons = payload.get("lessons") or []
        if payload.get("level") and len(lessons) >= 5:
            ok(f"list_lessons level={payload['level']} count={len(lessons)}")
        else:
            fail("list_lessons", str(payload))
            return

        first_id = lessons[0]["id"]
        detail = await get_lesson(db, student_id=student_id, lesson_id=first_id)
        if detail and detail.get("id") == first_id and detail.get("explanation"):
            ok(f"get_lesson {first_id} has explanation")
        else:
            fail("get_lesson", str(detail))

        missing = await get_lesson(db, student_id=student_id, lesson_id="ZZZ-grammar-99")
        if missing is None:
            ok("get_lesson returns None for unknown id")
        else:
            fail("get_lesson unknown", str(missing))


def main() -> int:
    test_curated_levels()
    test_stable_ids()
    test_routes_registered()
    asyncio.run(test_list_and_detail())
    print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
