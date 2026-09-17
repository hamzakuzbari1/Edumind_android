"""Verify Phase 8.0 promotion tests — curated banks, routes, grade flows, activity log.

Usage (from backend/):
    python scripts/verify_language_promotion.py
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


def test_curated_levels() -> None:
    from app.services.language_promotion_test_service import _CURATED, PASS_RATIO

    if PASS_RATIO == 0.8:
        ok("pass ratio 80%")
    else:
        fail("pass ratio", str(PASS_RATIO))

    for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
        qs = _CURATED.get(level, [])
        if len(qs) >= 4 and all(len(q.get("choices") or []) == 4 for q in qs):
            ok(f"curated bank {level} ({len(qs)} questions)")
        else:
            fail(f"curated bank {level}")


def test_schemas() -> None:
    from app.schemas.language_curriculum import PromotionResultOut, PromotionTestOut

    t = PromotionTestOut(test_id="abc", level="A1", eligible=True, next_level="A2")
    if t.next_level == "A2":
        ok("PromotionTestOut eligible fields")
    else:
        fail("PromotionTestOut")

    r = PromotionResultOut(score_percent=80, correct=4, total=5, passed=True, promoted=True, new_level="A2")
    if r.promoted and r.new_level == "A2":
        ok("PromotionResultOut")
    else:
        fail("PromotionResultOut")


def test_routes_registered() -> None:
    from app.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    for p in ("/api/student/languages/promotion-test", "/api/student/languages/promotion-test/submit"):
        if p in paths:
            ok(f"route registered {p}")
        else:
            fail(f"route missing {p}")


async def test_grade_flows() -> None:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.enrollment import PaymentStatus
    from app.models.language.engagement import LanguageActivityLog
    from app.models.language.subscription import LanguageSubscription
    from app.services.language_promotion_test_service import _tests, build_promotion_test, grade_promotion_test

    async with AsyncSessionLocal() as db:
        student_id = (
            await db.execute(
                select(LanguageSubscription.student_id)
                .where(LanguageSubscription.payment_status == PaymentStatus.paid)
                .limit(1)
            )
        ).scalar_one_or_none()
        if not student_id:
            ok("grade flows skipped (no paid subscriber)")
            return

        before = (
            await db.execute(
                select(LanguageActivityLog.id).where(
                    LanguageActivityLog.student_id == student_id,
                    LanguageActivityLog.event_type == "promotion_test_attempt",
                )
            )
        ).all()

        payload = await build_promotion_test(db, student_id=student_id)
        if not payload.get("test_id") or len(payload.get("questions") or []) < 4:
            fail("build_promotion_test", str(payload))
            return
        ok(f"build_promotion_test level={payload['level']} questions={len(payload['questions'])}")

        test_id = payload["test_id"]
        entry = _tests.get(test_id)
        if not entry:
            fail("_tests cache missing test_id")
            return

        _, level, key = entry
        wrong = {str(i): (ci + 1) % 4 for i, ci in enumerate(key)}
        fail_result = await grade_promotion_test(db, student_id=student_id, test_id=test_id, answers=wrong)
        if not fail_result["passed"] and not fail_result["promoted"]:
            ok("failure flow — not passed")
        else:
            fail("failure flow", str(fail_result))

        payload2 = await build_promotion_test(db, student_id=student_id)
        test_id2 = payload2["test_id"]
        entry2 = _tests.get(test_id2)
        if not entry2:
            fail("rebuild test for success flow")
            await db.rollback()
            return
        correct = {str(i): ci for i, ci in enumerate(entry2[2])}
        pass_result = await grade_promotion_test(db, student_id=student_id, test_id=test_id2, answers=correct)
        if pass_result["passed"]:
            ok(f"success flow — passed score={pass_result['score_percent']}%")
        else:
            fail("success flow", str(pass_result))

        after = (
            await db.execute(
                select(LanguageActivityLog.id).where(
                    LanguageActivityLog.student_id == student_id,
                    LanguageActivityLog.event_type == "promotion_test_attempt",
                )
            )
        ).all()
        if len(after) >= len(before) + 2:
            ok(f"activity log persisted attempts (+{len(after) - len(before)})")
        else:
            fail("activity log persistence", f"before={len(before)} after={len(after)}")

        await db.rollback()


def main() -> int:
    test_curated_levels()
    test_schemas()
    test_routes_registered()
    asyncio.run(test_grade_flows())
    print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
