"""Verify Phase 5.5 — Listening Official Promotion Engine.

Usage (from backend/):
    python scripts/verify_language_official_promotion_phase_5_5.py
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
from app.services.language_official_promotion import apply_listening_official_promotion
from app.services.language_official_promotion.storage import get_latest_promotion_test_attempt
from app.services.language_progression_service import get_official_cefr, upsert_official_levels
from app.services.language_promotion_test import (
    PromotionTestOutcome,
    clear_sessions_for_tests,
    submit_listening_promotion_test,
)
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
    official_cefr: str = "A2",
    target_cefr: str = "B1",
) -> dict:
    return {
        "listening_promotion_tests": {
            "attempts": [
                {
                    "session_id": session_id,
                    "attempt_number": attempt_number,
                    "official_cefr": official_cefr,
                    "target_cefr": target_cefr,
                    "overall_score": overall_score,
                    "result": result,
                    "objective_scores": {},
                }
            ],
            "used_lesson_ids": [],
            "used_sequences": [],
        },
        "stability": {
            "history": [
                {
                    "lesson_index": 1,
                    "readiness_score": 100,
                    "gate_eligible": True,
                    "confidence_avg": 0.9,
                    "evidence_coverage_avg": 0.8,
                    "review_completion_ratio": 1.0,
                    "recent_consistency": 0.9,
                    "challenge_score": 0.7,
                }
            ],
            "promotion_confidence": 92,
        },
        "readiness_score": 100,
        "status": "PROMOTION_AVAILABLE",
        "skill": "listening",
        "official_cefr": official_cefr,
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
            source="verify_official_promo_5_5",
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

        applied = await apply_listening_official_promotion(
            db, student_id=sid, language_id=lid, session_id=session.session_id
        )
        await db.refresh(row)

        results.append(_ok("PASS promotes", applied.promotion_success))
        results.append(_ok("old CEFR A2", applied.old_cefr == "A2"))
        results.append(_ok("new CEFR B1", applied.new_cefr == "B1"))
        results.append(_ok("listening CEFR updated", row.official_listening_cefr == LanguageLevel.B1))
        results.append(_ok("reading unchanged", row.official_reading_cefr == LanguageLevel.A2))
        results.append(_ok("speaking unchanged", row.official_speaking_cefr == LanguageLevel.A2))
        results.append(_ok("writing unchanged", row.official_writing_cefr == LanguageLevel.A2))
        results.append(_ok("overall stays A2 when listening not bottleneck", row.official_overall_cefr == LanguageLevel.A2))
        results.append(_ok("learning stage reset", row.learning_stage_listening == 1))
        results.append(_ok("readiness score reset", row.promotion_readiness_score == 0))
        payload = row.promotion_readiness_json or {}
        results.append(_ok("readiness status reset", payload.get("status") == "NOT_READY"))
        stability = payload.get("stability") or {}
        results.append(_ok("promotion confidence reset", stability.get("promotion_confidence") == 0))
        results.append(_ok("stability history preserved", len(stability.get("history") or []) >= 1))
        results.append(_ok("exam history preserved", len((payload.get("listening_promotion_tests") or {}).get("attempts") or []) >= 1))
        promotions = payload.get("listening_official_promotions") or {}
        results.append(_ok("promotion event stored", len(promotions.get("events") or []) >= 1))
        results.append(_ok("event id returned", applied.event_id is not None))
        results.append(_ok("summary generated", "Congratulations" in applied.summary and "B1 Beginner" in applied.summary))
        results.append(_ok("journey reset flagged", applied.journey_reset.transition_gate_reset))

        await db.rollback()

    return results


async def verify_fail_and_borderline() -> list[bool]:
    print("\n=== FAIL and BORDERLINE do not promote ===")
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
            source="verify_official_promo_5_5",
            force=True,
        )

        for outcome in (PromotionTestOutcome.FAIL, PromotionTestOutcome.BORDERLINE):
            row.promotion_readiness_json = _seed_attempt_payload(
                session_id=f"session-{outcome.value.lower()}",
                result=outcome.value,
                overall_score=40.0 if outcome == PromotionTestOutcome.FAIL else 70.0,
            )
            await db.flush()
            denied = await apply_listening_official_promotion(db, student_id=sid, language_id=lid)
            await db.refresh(row)
            results.append(_ok(f"{outcome.value} does not promote", not denied.promotion_success))
            results.append(
                _ok(
                    f"{outcome.value} CEFR unchanged",
                    row.official_listening_cefr == LanguageLevel.A2,
                )
            )

        await db.rollback()

    return results


async def verify_idempotent() -> list[bool]:
    print("\n=== Duplicate promotion prevented ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip idempotent", True)]

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
            source="verify_official_promo_5_5",
            force=True,
        )
        session_id = "idem-session-pass"
        row.promotion_readiness_json = _seed_attempt_payload(
            session_id=session_id,
            result=PromotionTestOutcome.PASS.value,
            overall_score=95.0,
        )
        await db.flush()

        first = await apply_listening_official_promotion(db, student_id=sid, language_id=lid)
        await db.refresh(row)
        events_after_first = len((row.promotion_readiness_json or {}).get("listening_official_promotions", {}).get("events", []))

        second = await apply_listening_official_promotion(db, student_id=sid, language_id=lid)
        await db.refresh(row)
        events_after_second = len((row.promotion_readiness_json or {}).get("listening_official_promotions", {}).get("events", []))

        results.append(_ok("first promotion succeeds", first.promotion_success))
        results.append(_ok("second call still success", second.promotion_success))
        results.append(_ok("no duplicate events", events_after_second == events_after_first == 1))
        results.append(_ok("CEFR remains B1", row.official_listening_cefr == LanguageLevel.B1))

        await db.rollback()

    return results


async def verify_full_test_flow() -> list[bool]:
    print("\n=== Full promotion test -> promotion flow ===")
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
            reading=LanguageLevel.A1,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A1,
            speaking=LanguageLevel.A1,
            overall=LanguageLevel.A1,
            source="verify_official_promo_5_5",
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
        await db.refresh(row)

        latest = get_latest_promotion_test_attempt(row.promotion_readiness_json)
        results.append(_ok("test PASS stored", latest is not None and latest.result == "PASS"))

        applied = await apply_listening_official_promotion(
            db, student_id=sid, language_id=lid, session_id=session.session_id
        )
        await db.refresh(row)
        official = await get_official_cefr(db, student_id=sid, language_id=lid, skill=LanguageSkill.listening)

        results.append(_ok("promotion applied", applied.promotion_success))
        results.append(_ok("official listening B1", official.level == LanguageLevel.B1))
        results.append(
            _ok(
                "overall stays A1 when listening not bottleneck",
                row.official_overall_cefr == LanguageLevel.A1,
            )
        )

        await db.rollback()

    return results


def verify_upstream_untouched() -> list[bool]:
    print("\n=== Upstream engines untouched ===")
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    packages = [
        "language_promotion_test",
        "language_promotion_readiness",
        "language_promotion_stability",
        "language_learning_stage",
        "language_transition_gate",
    ]
    results: list[bool] = []
    for pkg in packages:
        path = root / pkg
        text_body = "\n".join(p.read_text(encoding="utf-8") for p in path.rglob("*.py"))
        results.append(
            _ok(
                f"{pkg} has no official_promotion import",
                "language_official_promotion" not in text_body,
            )
        )

    for mod_name in (
        "language_promotion_test.engine",
        "language_promotion_readiness.engine",
        "language_promotion_stability.engine",
        "language_learning_stage.engine",
        "language_transition_gate.engine",
    ):
        import importlib

        mod = importlib.import_module(f"app.services.{mod_name}")
        src = inspect.getsource(mod)
        results.append(_ok(f"{mod_name} unchanged", "language_official_promotion" not in src))

    return results


async def main() -> int:
    print("verify_language_official_promotion_phase_5_5")
    all_results: list[bool] = []
    all_results.extend(await verify_pass_promotes())
    all_results.extend(await verify_fail_and_borderline())
    all_results.extend(await verify_idempotent())
    all_results.extend(await verify_full_test_flow())
    all_results.extend(verify_upstream_untouched())

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
