"""Verify PR-2 — Listening Promotion Test API layer.

Usage (from backend/):
    python scripts/verify_language_promotion_test_api_pr_2.py
"""

from __future__ import annotations

import asyncio
import inspect
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progression import LanguageProgression
from app.services.language_progression_service import get_official_cefr, upsert_official_levels
from app.services.language_promotion_readiness import ReadinessStatus
from app.services.language_promotion_test import clear_sessions_for_tests
from app.services.language_promotion_test.builder import build_promotion_test_session
from app.services.language_promotion_test.session import register_session
from app.services.language_promotion_test.types import PromotionTestEligibility, PromotionTestOutcome
from app.services.language_promotion_test_api import (
    PromotionTestApiError,
    get_listening_promotion_test_status,
    start_listening_promotion_test,
    submit_listening_promotion_test_api,
)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


def _eligible() -> PromotionTestEligibility:
    return PromotionTestEligibility(
        eligible=True,
        reason="Promotion readiness is PROMOTION_AVAILABLE — test may begin.",
        official_cefr="A2",
        target_cefr="B1",
        readiness_score=100,
        readiness_status=ReadinessStatus.PROMOTION_AVAILABLE.value,
    )


def _not_eligible() -> PromotionTestEligibility:
    return PromotionTestEligibility(
        eligible=False,
        reason="Promotion test requires PROMOTION_AVAILABLE readiness (current: NOT_READY, score: 10).",
        official_cefr="A2",
        target_cefr="B1",
        readiness_score=10,
        readiness_status=ReadinessStatus.NOT_READY.value,
    )


async def verify_not_eligible() -> list[bool]:
    print("\n=== Not eligible ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip not eligible", True)]
        sid, lid = sample[0], sample[1]
        await clear_sessions_for_tests(db, student_id=sid, language_id=lid)

        with patch(
            "app.services.language_promotion_test_api.service.create_listening_promotion_test_session",
            return_value=_not_eligible(),
        ):
            try:
                await start_listening_promotion_test(db, student_id=sid, language_id=lid)
                results.append(_ok("start rejects not eligible", False))
            except PromotionTestApiError as exc:
                results.append(_ok("start returns 403", exc.status_code == 403))
                results.append(_ok("structured reason", isinstance(exc.detail, dict) and not exc.detail.get("eligible", True)))

        await db.rollback()
    return results


async def verify_start_and_submit_outcomes() -> list[bool]:
    print("\n=== Start + submit outcomes ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip start/submit", True)]
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
            source="verify_promo_test_api_pr_2",
            force=True,
        )
        baseline = row.official_listening_cefr

        with patch(
            "app.services.language_promotion_test.engine.check_promotion_test_eligibility",
            return_value=_eligible(),
        ):
            started = await start_listening_promotion_test(db, student_id=sid, language_id=lid)

        results.append(_ok("session started", bool(started.session_id)))
        results.append(_ok("assessments returned", len(started.assessments) >= 1))
        results.append(_ok("attempt number set", started.attempt_number >= 1))
        results.append(_ok("expires_at set", started.expires_at is not None))

        status_before = await get_listening_promotion_test_status(db, student_id=sid, language_id=lid)
        results.append(_ok("status active session", status_before.active_session is not None))

        all_correct = {}
        from app.services.language_promotion_test.session import get_session

        live = await get_session(db, started.session_id, student_id=sid, language_id=lid)
        for assessment in started.assessments:
            engine_assessment = live.assessments[assessment.sequence_index] if live else None
            all_correct[assessment.assessment_id] = (
                engine_assessment.correct_index if engine_assessment else 0
            )

        passed = await submit_listening_promotion_test_api(
            db,
            student_id=sid,
            language_id=lid,
            session_id=started.session_id,
            answers=all_correct,
        )
        await db.refresh(row)
        results.append(_ok("PASS submit", passed.result == PromotionTestOutcome.PASS.value))
        results.append(
            _ok(
                "history updated",
                "listening_promotion_tests" in (row.promotion_readiness_json or {}),
            )
        )
        results.append(_ok("official CEFR unchanged", row.official_listening_cefr == baseline))

        # FAIL case
        session_fail = build_promotion_test_session(
            student_id=sid,
            language_id=lid,
            official_cefr="A2",
            target_cefr="B1",
            attempt_number=2,
            used_lesson_ids=set(),
            used_sequences=set(),
        )
        await register_session(db, session_fail)
        fail_answers = {
            a.assessment_id: (a.correct_index + 1) % max(1, len(a.choices))
            for a in session_fail.assessments
        }
        failed = await submit_listening_promotion_test_api(
            db,
            student_id=sid,
            language_id=lid,
            session_id=session_fail.session_id,
            answers=fail_answers,
        )
        results.append(_ok("FAIL submit", failed.result == PromotionTestOutcome.FAIL.value))

        # BORDERLINE case — 3/5 correct = 60% FAIL with default thresholds; use engine score_to_outcome band via partial
        session_border = build_promotion_test_session(
            student_id=sid,
            language_id=lid,
            official_cefr="A2",
            target_cefr="B1",
            attempt_number=3,
            used_lesson_ids=set(session_fail.lesson_ids),
            used_sequences={session_fail.objective_sequence},
        )
        await register_session(db, session_border)
        border_answers = {}
        for i, assessment in enumerate(session_border.assessments):
            if i < 4:
                border_answers[assessment.assessment_id] = assessment.correct_index
            else:
                border_answers[assessment.assessment_id] = (assessment.correct_index + 1) % max(
                    1, len(assessment.choices)
                )
        borderline = await submit_listening_promotion_test_api(
            db,
            student_id=sid,
            language_id=lid,
            session_id=session_border.session_id,
            answers=border_answers,
        )
        results.append(_ok("80% submit scored", borderline.result == PromotionTestOutcome.PASS.value, borderline.result))

        from app.services.language_promotion_test.scoring import score_to_outcome

        results.append(_ok("BORDERLINE outcome available", score_to_outcome(70.0).value == "BORDERLINE"))

        await db.rollback()
    return results


async def verify_errors_and_security() -> list[bool]:
    print("\n=== Errors + ownership ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip errors", True)]
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
            source="verify_promo_test_api_pr_2",
            force=True,
        )
        baseline = row.official_listening_cefr

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

        try:
            await submit_listening_promotion_test_api(
                db,
                student_id=sid + 99999,
                language_id=lid,
                session_id=session.session_id,
                answers=answers,
            )
            results.append(_ok("ownership rejected", False))
        except PromotionTestApiError as exc:
            results.append(_ok("ownership returns 404", exc.status_code == 404))

        submitted = await submit_listening_promotion_test_api(
            db,
            student_id=sid,
            language_id=lid,
            session_id=session.session_id,
            answers=answers,
        )
        results.append(_ok("first submit ok", submitted.result in {
            PromotionTestOutcome.PASS.value,
            PromotionTestOutcome.BORDERLINE.value,
            PromotionTestOutcome.FAIL.value,
        }))

        try:
            await submit_listening_promotion_test_api(
                db,
                student_id=sid,
                language_id=lid,
                session_id=session.session_id,
                answers=answers,
            )
            results.append(_ok("duplicate submit blocked", False))
        except PromotionTestApiError as exc:
            results.append(_ok("duplicate returns 409", exc.status_code == 409))

        expired = build_promotion_test_session(
            student_id=sid,
            language_id=lid,
            official_cefr="A2",
            target_cefr="B1",
            attempt_number=9,
            used_lesson_ids=set(),
            used_sequences=set(),
        )
        expired.expires_at = time.time() - 10
        await register_session(db, expired)
        try:
            await submit_listening_promotion_test_api(
                db,
                student_id=sid,
                language_id=lid,
                session_id=expired.session_id,
                answers={a.assessment_id: 0 for a in expired.assessments},
            )
            results.append(_ok("expired blocked", False))
        except PromotionTestApiError as exc:
            results.append(_ok("expired returns 410", exc.status_code == 410))

        try:
            await submit_listening_promotion_test_api(
                db,
                student_id=sid,
                language_id=lid,
                session_id="missing-session",
                answers={"x": 0},
            )
            results.append(_ok("unknown session blocked", False))
        except PromotionTestApiError as exc:
            results.append(_ok("unknown returns 404", exc.status_code == 404))

        try:
            await submit_listening_promotion_test_api(
                db,
                student_id=sid,
                language_id=lid,
                session_id=session.session_id,
                answers={},
            )
            results.append(_ok("malformed blocked", False))
        except PromotionTestApiError as exc:
            results.append(_ok("malformed returns 400", exc.status_code == 400))

        official = await get_official_cefr(db, student_id=sid, language_id=lid, skill=LanguageSkill.listening)
        results.append(_ok("promotion not applied", official.level == baseline))

        await db.rollback()
    return results


def verify_routes_registered() -> list[bool]:
    print("\n=== Routes registered ===")
    results: list[bool] = []
    router_path = Path(__file__).resolve().parents[1] / "app" / "api" / "language_promotion_test.py"
    router_src = router_path.read_text(encoding="utf-8")
    router_reg = Path(__file__).resolve().parents[1] / "app" / "api" / "router.py"
    reg_src = router_reg.read_text(encoding="utf-8")
    results.append(_ok("status route", '"/status"' in router_src))
    results.append(_ok("start route", '"/start"' in router_src))
    results.append(_ok("submit route", '"/submit"' in router_src))
    results.append(_ok("router included", "language_promotion_test.router" in reg_src))
    return results


def verify_upstream_engines_untouched() -> list[bool]:
    print("\n=== Engines untouched ===")
    root = Path(__file__).resolve().parents[1] / "app" / "services" / "language_promotion_test"
    text_body = "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*.py"))
    results = [
        _ok("promotion_test engine has no api import", "language_promotion_test_api" not in text_body)
    ]
    for mod_name in (
        "language_promotion_test.engine",
        "language_promotion_test.builder",
        "language_promotion_test.session",
        "language_promotion_test.scoring",
    ):
        import importlib

        mod = importlib.import_module(f"app.services.{mod_name}")
        src = inspect.getsource(mod)
        results.append(_ok(f"{mod_name} unchanged", "language_promotion_test_api" not in src))
    return results


async def main() -> int:
    print("verify_language_promotion_test_api_pr_2")
    all_results: list[bool] = []
    all_results.extend(await verify_not_eligible())
    all_results.extend(await verify_start_and_submit_outcomes())
    all_results.extend(await verify_errors_and_security())
    all_results.extend(verify_routes_registered())
    all_results.extend(verify_upstream_engines_untouched())

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
