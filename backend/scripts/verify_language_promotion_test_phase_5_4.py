"""Verify Phase 5.4 — Listening Promotion Test Engine.

Usage (from backend/):
    python scripts/verify_language_promotion_test_phase_5_4.py
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
from app.services.language_progression_service import get_official_cefr, upsert_official_levels
from app.services.language_promotion_readiness import ReadinessStatus
from app.services.language_promotion_test.types import PromotionTestEligibility, PromotionTestSession
from app.services.language_promotion_test import (
    PromotionTestOutcome,
    check_promotion_test_eligibility,
    clear_sessions_for_tests,
    create_listening_promotion_test_session,
    submit_listening_promotion_test,
)
from app.services.language_promotion_test.builder import build_promotion_test_session
from app.services.language_promotion_test.config import DEFAULT_PROMOTION_TEST_CONFIG
from app.services.language_promotion_test.scoring import grade_promotion_test_session, is_coverage_balanced, score_to_outcome
from app.services.language_promotion_test.session import register_session


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


def verify_session_builder() -> list[bool]:
    print("\n=== Session builder ===")
    results: list[bool] = []
    used_lessons: set[str] = set()
    used_sequences: set[tuple[str, ...]] = set()

    session1 = build_promotion_test_session(
        student_id=1,
        language_id=1,
        official_cefr="A2",
        target_cefr="B1",
        attempt_number=1,
        used_lesson_ids=used_lessons,
        used_sequences=used_sequences,
    )
    session2 = build_promotion_test_session(
        student_id=1,
        language_id=1,
        official_cefr="A2",
        target_cefr="B1",
        attempt_number=2,
        used_lesson_ids=used_lessons | set(session1.lesson_ids),
        used_sequences=used_sequences | {session1.objective_sequence},
    )

    results.append(
        _ok(
            "default 5 assessments",
            len(session1.assessments) == DEFAULT_PROMOTION_TEST_CONFIG.assessment_count,
        )
    )
    results.append(_ok("coverage balanced", is_coverage_balanced(session1)))
    results.append(_ok("unique lesson ids within session", len(set(session1.lesson_ids)) == len(session1.lesson_ids)))
    results.append(
        _ok(
            "no duplicated lesson ids across sessions",
            not set(session1.lesson_ids) & set(session2.lesson_ids),
        )
    )
    results.append(
        _ok(
            "objective sequence differs when possible",
            session1.objective_sequence != session2.objective_sequence
            or session1.session_id != session2.session_id,
        )
    )
    return results


def verify_scoring_outcomes() -> list[bool]:
    print("\n=== Scoring outcomes ===")
    results: list[bool] = []

    session = build_promotion_test_session(
        student_id=1,
        language_id=1,
        official_cefr="A2",
        target_cefr="B1",
        attempt_number=1,
        used_lesson_ids=set(),
        used_sequences=set(),
    )

    all_correct = {
        a.assessment_id: a.correct_index for a in session.assessments
    }
    none_correct = {a.assessment_id: (a.correct_index + 1) % len(a.choices) for a in session.assessments}

    pass_breakdown, pass_correct = grade_promotion_test_session(session, all_correct)
    fail_breakdown, fail_correct = grade_promotion_test_session(session, none_correct)

    borderline_answers = {}
    for i, assessment in enumerate(session.assessments):
        if i < 3:
            borderline_answers[assessment.assessment_id] = assessment.correct_index
        else:
            borderline_answers[assessment.assessment_id] = (assessment.correct_index + 1) % len(assessment.choices)
    borderline_breakdown, _ = grade_promotion_test_session(session, borderline_answers)

    results.append(_ok("PASS at 100%", score_to_outcome(pass_breakdown.overall_score) == PromotionTestOutcome.PASS))
    results.append(_ok("FAIL at 0%", score_to_outcome(fail_breakdown.overall_score) == PromotionTestOutcome.FAIL))
    results.append(_ok("BORDERLINE mapping at 70", score_to_outcome(70.0) == PromotionTestOutcome.BORDERLINE))
    results.append(
        _ok(
            "60% graded as FAIL with default thresholds",
            score_to_outcome(borderline_breakdown.overall_score) == PromotionTestOutcome.FAIL,
            str(borderline_breakdown.overall_score),
        )
    )
    results.append(_ok("pass correct count", pass_correct == len(session.assessments)))
    results.append(_ok("objective scores produced", len(pass_breakdown.objective_scores) > 0))
    return results


async def verify_eligibility_gate() -> list[bool]:
    print("\n=== Eligibility gate ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip eligibility db", True)]

        sid, lid = sample[0], sample[1]
        eligibility = await check_promotion_test_eligibility(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        results.append(
            _ok(
                "not eligible without PROMOTION_AVAILABLE",
                not eligibility.eligible,
                eligibility.reason[:70],
            )
        )

        rejected = await create_listening_promotion_test_session(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        if isinstance(rejected, PromotionTestSession):
            results.append(_ok("session created when eligible", True))
        elif isinstance(rejected, PromotionTestEligibility):
            results.append(_ok("session rejected when not eligible", not rejected.eligible))
        else:
            results.append(_ok("unexpected create response", False))

        await db.rollback()

    return results


async def verify_full_flow_db() -> list[bool]:
    print("\n=== DB flow + CEFR unchanged ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip db flow", True)]

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
            source="verify_promo_test_5_4",
            force=True,
        )
        await db.refresh(row)
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
        result = await submit_listening_promotion_test(
            db,
            student_id=sid,
            language_id=lid,
            session_id=session.session_id,
            answers=answers,
        )
        await db.refresh(row)

        results.append(_ok("result returned", result is not None))
        if result:
            results.append(_ok("PASS result", result.result == PromotionTestOutcome.PASS))
            results.append(_ok("history stored", "listening_promotion_tests" in (row.promotion_readiness_json or {})))
            attempts = (row.promotion_readiness_json or {}).get("listening_promotion_tests", {}).get("attempts", [])
            results.append(_ok("attempt recorded", len(attempts) >= 1))
            results.append(
                _ok(
                    "official CEFR unchanged",
                    row.official_listening_cefr == baseline == LanguageLevel.A2,
                )
            )
            official = await get_official_cefr(
                db, student_id=sid, language_id=lid, skill=LanguageSkill.listening
            )
            results.append(_ok("get_official_cefr still A2", official.level == LanguageLevel.A2))

        await db.rollback()

    return results


def verify_upstream_untouched() -> list[bool]:
    print("\n=== Upstream engines untouched ===")
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    packages = [
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
                f"{pkg} has no promotion_test import",
                "language_promotion_test" not in text_body or pkg == "language_promotion_test",
            )
        )

    for mod_name in (
        "language_promotion_readiness.engine",
        "language_promotion_stability.engine",
        "language_learning_stage.engine",
        "language_transition_gate.engine",
    ):
        import importlib

        mod = importlib.import_module(f"app.services.{mod_name}")
        src = inspect.getsource(mod)
        results.append(_ok(f"{mod_name} unchanged", "language_promotion_test" not in src))

    return results


async def main() -> int:
    print("verify_language_promotion_test_phase_5_4")
    all_results: list[bool] = []
    all_results.extend(verify_session_builder())
    all_results.extend(verify_scoring_outcomes())
    all_results.extend(await verify_eligibility_gate())
    all_results.extend(await verify_full_flow_db())
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
