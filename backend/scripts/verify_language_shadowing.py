"""Verify Phase 7.9 shadowing — sentences, pronunciation helpers, routes, activity log.

Usage (from backend/):
    python scripts/verify_language_shadowing.py
"""

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


def test_shadow_sentences_constants() -> None:
    from app.services.language_shadowing_service import PASS_PRONUNCIATION, PASS_SIMILARITY, SHADOW_SENTENCES

    if PASS_SIMILARITY == 70 and PASS_PRONUNCIATION == 70:
        ok("pass thresholds 70/70")
    else:
        fail("pass thresholds", f"{PASS_SIMILARITY}/{PASS_PRONUNCIATION}")

    for level in ("A1", "A2", "B1", "B2", "C1"):
        if level in SHADOW_SENTENCES and len(SHADOW_SENTENCES[level]) >= 5:
            ok(f"SHADOW_SENTENCES[{level}] has >=5 items")
        else:
            fail(f"SHADOW_SENTENCES[{level}]")


def test_word_similarity() -> None:
    from app.services.language_pronunciation_service import word_similarity

    if word_similarity("hello world", "hello world") == 100:
        ok("word_similarity exact match")
    else:
        fail("word_similarity exact", str(word_similarity("hello world", "hello world")))

    partial = word_similarity("hello there", "hello world")
    if 40 <= partial <= 60:
        ok("word_similarity partial overlap")
    else:
        fail("word_similarity partial", str(partial))


def test_schemas() -> None:
    from app.schemas.language_learning import ShadowSentenceListOut, ShadowSubmitOut

    out = ShadowSentenceListOut(level="A1", sentences=[{"id": 1, "text": "Hi", "level": "A1", "source": "level"}])
    if out.level == "A1" and len(out.sentences) == 1:
        ok("ShadowSentenceListOut schema")
    else:
        fail("ShadowSentenceListOut")

    submit = ShadowSubmitOut(similarity=80, overall_score=75, passed=True)
    if submit.passed and submit.similarity == 80:
        ok("ShadowSubmitOut schema")
    else:
        fail("ShadowSubmitOut")


def test_routes_registered() -> None:
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    needed = [
        "/api/student/languages/speaking/shadow/sentences",
        "/api/student/languages/speaking/shadow",
    ]
    for p in needed:
        if p in paths:
            ok(f"route registered {p}")
        else:
            fail(f"route missing {p}")


async def test_db_checks() -> None:
    from sqlalchemy import func, select

    from app.db.session import AsyncSessionLocal
    from app.models.enrollment import PaymentStatus
    from app.models.language.engagement import LanguageActivityLog
    from app.models.language.subscription import LanguageSubscription
    from app.services.language_shadowing_service import list_shadow_sentences

    async with AsyncSessionLocal() as db:
        sub = (
            await db.execute(
                select(LanguageSubscription.student_id)
                .where(LanguageSubscription.payment_status == PaymentStatus.paid)
                .limit(1)
            )
        ).scalar_one_or_none()
        if not sub:
            ok("list_shadow_sentences skipped (no paid language subscriber)")
        else:
            payload = await list_shadow_sentences(db, student_id=sub)
            if payload.get("level") and len(payload.get("sentences") or []) >= 5:
                ok(f"list_shadow_sentences returns {len(payload['sentences'])} sentences at {payload['level']}")
            else:
                fail("list_shadow_sentences payload", str(payload))

        count = (
            await db.execute(
                select(func.count()).select_from(LanguageActivityLog).where(
                    LanguageActivityLog.event_type == "shadowing_attempt"
                )
            )
        ).scalar_one()
        ok(f"shadowing_attempt event type queryable (existing rows={count})")


def main() -> int:
    test_shadow_sentences_constants()
    test_word_similarity()
    test_schemas()
    test_routes_registered()
    asyncio.run(test_db_checks())
    print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
