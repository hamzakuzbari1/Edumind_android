"""Verify Phase 8.1 vocabulary spaced repetition — SM-2, routes, queue, persistence.

Usage (from backend/):
    python scripts/verify_language_vocabulary_sr.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
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


def test_compute_sm2_examples() -> None:
    from app.services.language_vocabulary_sr_service import compute_sm2

    ease, interval, rep = compute_sm2(2.5, 1, 0, 5)
    if ease == 2.6 and interval == 1 and rep == 1:
        ok("SM2 quality=5 first review -> interval 1, rep 1, ease 2.6")
    else:
        fail("SM2 first pass", f"{ease}/{interval}/{rep}")

    ease, interval, rep = compute_sm2(2.5, 6, 1, 5)
    if interval == 6 and rep == 2:
        ok("SM2 second pass -> interval 6, rep 2")
    else:
        fail("SM2 second pass", f"{interval}/{rep}")

    ease, interval, rep = compute_sm2(2.5, 50, 9, 1)
    if interval == 1 and rep == 0:
        ok("SM2 forgotten (quality=1) resets interval and repetition")
    else:
        fail("SM2 forgotten", f"{interval}/{rep}")


def test_routes_registered() -> None:
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    for p in (
        "/api/student/languages/vocabulary/review",
        "/api/student/languages/vocabulary/stats",
    ):
        if p in paths:
            ok(f"route registered {p}")
        else:
            fail(f"route missing {p}")


async def test_review_flows() -> None:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.enrollment import PaymentStatus
    from app.models.language.engagement import LanguageActivityLog
    from app.models.language.enums import LanguageVocabularyStatus
    from app.models.language.progress import LanguageVocabularyProgress
    from app.models.language.subscription import LanguageSubscription
    from app.services.language_subscription_service import get_default_language
    from app.services.language_vocabulary_sr_service import (
        count_due,
        get_review_queue,
        submit_review,
        upsert_vocabulary_with_sr,
    )

    async with AsyncSessionLocal() as db:
        student_id = (
            await db.execute(
                select(LanguageSubscription.student_id)
                .where(LanguageSubscription.payment_status == PaymentStatus.paid)
                .limit(1)
            )
        ).scalar_one_or_none()
        if not student_id:
            ok("review flows skipped (no paid subscriber)")
            return

        language = await get_default_language(db)
        lemma = f"sr_verify_{int(datetime.now(timezone.utc).timestamp())}"
        await upsert_vocabulary_with_sr(
            db, student_id=student_id, language_id=language.id, lemmas=[lemma]
        )
        await db.flush()

        row = (
            await db.execute(
                select(LanguageVocabularyProgress).where(
                    LanguageVocabularyProgress.student_id == student_id,
                    LanguageVocabularyProgress.lemma == lemma,
                )
            )
        ).scalar_one()
        if row.next_review_at and row.ease_factor == 2.5:
            ok("upsert sets next_review_at and ease_factor=2.5")
        else:
            fail("upsert SR fields", f"next={row.next_review_at} ease={row.ease_factor}")

        due_before = await count_due(db, student_id=student_id, language_id=language.id)
        queue = await get_review_queue(db, student_id=student_id, language_id=language.id, limit=50)
        ids = {item["vocabulary_id"] for item in queue}
        if row.id in ids:
            ok("review queue includes new lemma")
        else:
            fail("review queue", f"id {row.id} not in queue of {len(queue)}")

        wrong = await submit_review(db, student_id=student_id, vocabulary_id=row.id, quality=1)
        if wrong["new_status"] == LanguageVocabularyStatus.new.value and wrong["interval_days"] == 1:
            ok("incorrect answer flow resets to new, interval 1")
        else:
            fail("incorrect flow", str(wrong))

        row2 = await db.get(LanguageVocabularyProgress, row.id)
        right = await submit_review(db, student_id=student_id, vocabulary_id=row2.id, quality=5)
        if right["repetition_number"] == 1 and right["interval_days"] == 1:
            ok("correct answer flow -> rep 1, interval 1")
        else:
            fail("correct flow", str(right))

        logs = (
            await db.execute(
                select(LanguageActivityLog.id).where(
                    LanguageActivityLog.student_id == student_id,
                    LanguageActivityLog.event_type == "vocabulary_reviewed",
                )
            )
        ).all()
        if len(logs) >= 2:
            ok(f"vocabulary_reviewed activity logged ({len(logs)} rows)")
        else:
            fail("activity log", f"count={len(logs)}")

        await db.rollback()


def main() -> int:
    test_compute_sm2_examples()
    test_routes_registered()
    asyncio.run(test_review_flows())
    print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
