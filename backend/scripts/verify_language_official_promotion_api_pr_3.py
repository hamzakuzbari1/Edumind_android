"""Verify PR-3 — Listening Official Promotion API layer.

Usage (from backend/):
    python scripts/verify_language_official_promotion_api_pr_3.py
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progression import LanguageProgression
from app.services.language_official_promotion_api import (
    OfficialPromotionApiError,
    apply_listening_official_promotion_api,
)
from app.services.language_progression_service import get_official_cefr, upsert_official_levels
from app.services.language_promotion_test import PromotionTestOutcome, clear_sessions_for_tests
from app.services.language_promotion_test.builder import build_promotion_test_session
from app.services.language_promotion_test.scoring import grade_promotion_test_session
from app.services.language_promotion_test.session import register_session
from app.services.language_promotion_test.storage import save_promotion_test_attempt
from app.services.language_promotion_test.telemetry import build_promotion_test_result


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


def _seed_attempt_payload(
    *,
    session_id: str,
    result: str,
    overall_score: float,
    attempt_number: int = 1,
) -> dict:
    return {
        "listening_promotion_tests": {
            "attempts": [
                {
                    "session_id": session_id,
                    "attempt_number": attempt_number,
                    "official_cefr": "A2",
                    "target_cefr": "B1",
                    "overall_score": overall_score,
                    "result": result,
                    "objective_scores": {},
                }
            ],
            "used_lesson_ids": [],
            "used_sequences": [],
        },
        "stability": {"history": [{"lesson_index": 1, "readiness_score": 100}], "promotion_confidence": 92},
        "readiness_score": 100,
        "status": "PROMOTION_AVAILABLE",
        "skill": "listening",
        "official_cefr": "A2",
    }


async def verify_pass_promotes() -> list[bool]:
    print("\n=== PASS promotes ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip pass promotes", True)]

        sid, lid = sample[0], sample[1]
        await clear_sessions_for_tests(db, student_id=sid, language_id=lid)
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_official_promo_api_pr_3",
            force=True,
        )
        row.learning_stage_listening = 3
        row.promotion_readiness_score = 100

        session = build_promotion_test_session(
            student_id=sid,
            language_id=lid,
            official_cefr="A2",
            target_cefr="B1",
            attempt_number=1,
            used_lesson_ids=set(),
            used_sequences=set(),
        )
        row.promotion_readiness_json = _seed_attempt_payload(
            session_id=session.session_id,
            result=PromotionTestOutcome.PASS.value,
            overall_score=100.0,
        )
        await db.flush()

        applied = await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
        await db.refresh(row)

        results.append(_ok("promotion_success", applied.promotion_success))
        results.append(_ok("old CEFR A2", applied.old_cefr == "A2"))
        results.append(_ok("new CEFR B1", applied.new_cefr == "B1"))
        results.append(_ok("listening CEFR updated", row.official_listening_cefr == LanguageLevel.B1))
        results.append(_ok("learning stage reset", row.learning_stage_listening == 1))
        results.append(_ok("readiness reset", row.promotion_readiness_score == 0))
        promotions = (row.promotion_readiness_json or {}).get("listening_official_promotions") or {}
        results.append(_ok("promotion history stored", len(promotions.get("events") or []) >= 1))
        results.append(_ok("summary returned", "Congratulations" in applied.summary))
        results.append(_ok("event id returned", applied.event_id is not None))

        await db.rollback()

    return results


async def verify_fail_and_borderline() -> list[bool]:
    print("\n=== FAIL and BORDERLINE rejected ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip fail/borderline", True)]

        sid, lid = sample[0], sample[1]
        await clear_sessions_for_tests(db, student_id=sid, language_id=lid)
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_official_promo_api_pr_3",
            force=True,
        )

        for outcome in (PromotionTestOutcome.FAIL, PromotionTestOutcome.BORDERLINE):
            row.promotion_readiness_json = _seed_attempt_payload(
                session_id=f"session-{outcome.value.lower()}",
                result=outcome.value,
                overall_score=40.0 if outcome == PromotionTestOutcome.FAIL else 70.0,
            )
            await db.flush()
            try:
                await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
                results.append(_ok(f"{outcome.value} rejected", False))
            except OfficialPromotionApiError as exc:
                results.append(_ok(f"{outcome.value} returns 409", exc.status_code == 409))
                detail = exc.detail if isinstance(exc.detail, dict) else {}
                results.append(
                    _ok(
                        f"{outcome.value} promotion_success false",
                        detail.get("promotion_success") is False,
                    )
                )
            await db.refresh(row)
            results.append(
                _ok(
                    f"{outcome.value} CEFR unchanged",
                    row.official_listening_cefr == LanguageLevel.A2,
                )
            )

        await db.rollback()

    return results


async def verify_no_test_and_duplicate() -> list[bool]:
    print("\n=== No test + duplicate promotion ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip duplicate", True)]

        sid, lid = sample[0], sample[1]
        await clear_sessions_for_tests(db, student_id=sid, language_id=lid)
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_official_promo_api_pr_3",
            force=True,
        )
        row.promotion_readiness_json = None
        await db.flush()

        try:
            await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
            results.append(_ok("no test rejected", False))
        except OfficialPromotionApiError as exc:
            results.append(_ok("no test returns 404", exc.status_code == 404))

        session_id = "idem-api-pass"
        row.promotion_readiness_json = _seed_attempt_payload(
            session_id=session_id,
            result=PromotionTestOutcome.PASS.value,
            overall_score=95.0,
        )
        await db.flush()

        first = await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
        await db.refresh(row)
        events_after_first = len(
            (row.promotion_readiness_json or {}).get("listening_official_promotions", {}).get("events", [])
        )

        try:
            second = await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
            results.append(_ok("duplicate raises 409", False, str(second.promotion_success)))
        except OfficialPromotionApiError as exc:
            results.append(_ok("duplicate returns 409", exc.status_code == 409))
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            results.append(_ok("duplicate includes promotion info", detail.get("promotion_success") is True))

        await db.refresh(row)
        events_after_second = len(
            (row.promotion_readiness_json or {}).get("listening_official_promotions", {}).get("events", [])
        )
        results.append(_ok("first promotion ok", first.promotion_success))
        results.append(_ok("no duplicate events", events_after_second == events_after_first == 1))

        official = await get_official_cefr(db, student_id=sid, language_id=lid, skill=LanguageSkill.listening)
        results.append(_ok("official listening B1", official.level == LanguageLevel.B1))

        await db.rollback()

    return results


async def verify_full_flow() -> list[bool]:
    print("\n=== Full test submit -> promote flow ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip full flow", True)]

        sid, lid = sample[0], sample[1]
        await clear_sessions_for_tests(db, student_id=sid, language_id=lid)
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_official_promo_api_pr_3",
            force=True,
        )

        session = build_promotion_test_session(
            student_id=sid,
            language_id=lid,
            official_cefr="A2",
            target_cefr="B1",
            attempt_number=1,
            used_lesson_ids=set(),
            used_sequences=set(),
        )
        await register_session(db, session)
        answers = {a.assessment_id: a.correct_index for a in session.assessments}
        breakdown, correct = grade_promotion_test_session(session, answers)
        test_result = build_promotion_test_result(
            session=session, breakdown=breakdown, correct_count=correct
        )
        await save_promotion_test_attempt(
            db, student_id=sid, language_id=lid, session=session, result=test_result
        )

        applied = await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
        await db.refresh(row)
        results.append(_ok("full flow promotion_success", applied.promotion_success))
        results.append(_ok("full flow CEFR B1", row.official_listening_cefr == LanguageLevel.B1))

        await db.rollback()

    return results


def verify_routes_registered() -> list[bool]:
    print("\n=== Routes registered ===")
    results: list[bool] = []
    router_path = Path(__file__).resolve().parents[1] / "app" / "api" / "language_official_promotion.py"
    router_src = router_path.read_text(encoding="utf-8")
    reg_src = (Path(__file__).resolve().parents[1] / "app" / "api" / "router.py").read_text(encoding="utf-8")
    results.append(_ok("promote route", '"/promote"' in router_src))
    results.append(_ok("router included", "language_official_promotion.router" in reg_src))
    return results


def verify_engine_untouched() -> list[bool]:
    print("\n=== Official Promotion Engine untouched ===")
    root = Path(__file__).resolve().parents[1] / "app" / "services" / "language_official_promotion"
    text_body = "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*.py"))
    results = [
        _ok("engine has no api import", "language_official_promotion_api" not in text_body)
    ]
    import importlib

    mod = importlib.import_module("app.services.language_official_promotion.engine")
    src = inspect.getsource(mod)
    results.append(_ok("engine module unchanged", "language_official_promotion_api" not in src))
    return results


async def main() -> int:
    print("verify_language_official_promotion_api_pr_3")
    all_results: list[bool] = []
    all_results.extend(await verify_pass_promotes())
    all_results.extend(await verify_fail_and_borderline())
    all_results.extend(await verify_no_test_and_duplicate())
    all_results.extend(await verify_full_flow())
    all_results.extend(verify_routes_registered())
    all_results.extend(verify_engine_untouched())

    passed = sum(all_results)
    total = len(all_results)
    print(f"\n=== SUMMARY: {passed}/{total} checks passed ===")
    if passed == total:
        print("PASS")
        return 0
    print("FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
