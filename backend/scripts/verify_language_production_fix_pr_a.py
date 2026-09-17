"""Verify PR-A — Critical production fixes (commits + readiness JSON merge).

Usage (from backend/):
    python scripts/verify_language_production_fix_pr_a.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel
from app.models.language.progression import LanguageProgression
from app.services.language_listening_progression.runtime import run_listening_progression_after_submit
from app.services.language_official_promotion_api import apply_listening_official_promotion_api
from app.services.language_progression_service import upsert_official_levels
from app.services.language_promotion_readiness.storage import save_listening_promotion_readiness
from app.services.language_promotion_readiness.types import (
    PromotionReadinessResult,
    PromotionReadinessTelemetry,
    ReadinessStatus,
)
from app.services.language_promotion_test import PromotionTestOutcome, clear_sessions_for_tests
from app.services.language_promotion_test.builder import build_promotion_test_session
from app.services.language_promotion_test.session import register_session
from app.services.language_promotion_test.storage import load_promotion_test_state, save_promotion_test_attempt
from app.services.language_promotion_test.telemetry import build_promotion_test_result
from app.services.language_promotion_test.scoring import grade_promotion_test_session
from app.services.language_promotion_test_api import submit_listening_promotion_test_api


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


def _minimal_readiness_result(*, readiness_score: int = 42, official_cefr: str = "A2") -> PromotionReadinessResult:
    telemetry = PromotionReadinessTelemetry(
        official_cefr=official_cefr,
        persistent_stage=1,
        stage_score=50,
        gate_overall_score=0.5,
        gate_eligible=False,
        dimension_scores=(),
    )
    return PromotionReadinessResult(
        official_cefr=official_cefr,
        readiness_score=readiness_score,
        status=ReadinessStatus.NOT_READY,
        estimated_remaining=0.5,
        primary_blockers=("verify blocker",),
        secondary_blockers=(),
        strengths=(),
        next_actions=(),
        telemetry=telemetry,
    )


def _rich_json_payload(*, session_id: str = "sess-pr-a-1") -> dict:
    return {
        "skill": "listening",
        "official_cefr": "A2",
        "readiness_score": 100,
        "status": "PROMOTION_AVAILABLE",
        "listening_promotion_tests": {
            "attempts": [
                {
                    "session_id": session_id,
                    "attempt_number": 1,
                    "official_cefr": "A2",
                    "target_cefr": "B1",
                    "overall_score": 85.0,
                    "result": PromotionTestOutcome.PASS.value,
                    "objective_scores": {},
                }
            ],
            "used_lesson_ids": [],
            "used_sequences": [],
        },
        "stability": {
            "promotion_confidence": 88,
            "history": [{"lesson_index": 3, "readiness_score": 90}],
        },
        "listening_official_promotions": {
            "events": [{"session_id": "prev-promo", "new_cefr": "A2"}],
            "promoted_session_ids": ["prev-promo"],
        },
        "custom_future_key": {"nested": True, "version": 1},
    }


async def _sample_progression(db) -> tuple[int, int] | None:
    sample = (
        await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
    ).first()
    if sample is None:
        return None
    return int(sample[0]), int(sample[1])


async def verify_readiness_merge_preserves_buckets() -> list[bool]:
    print("\n=== Readiness merge preserves buckets ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_progression(db)
        if ids is None:
            return [_ok("skip merge (no progression row)", True)]

        sid, lid = ids
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        row.promotion_readiness_json = _rich_json_payload(session_id="merge-test-session")
        await db.flush()

        await save_listening_promotion_readiness(
            db,
            student_id=sid,
            language_id=lid,
            result=_minimal_readiness_result(readiness_score=55),
        )
        await db.refresh(row)
        payload = row.promotion_readiness_json or {}

        tests = payload.get("listening_promotion_tests") or {}
        attempts = tests.get("attempts") or []
        results.append(_ok("promotion test attempts preserved", len(attempts) == 1))
        results.append(
            _ok(
                "attempt session_id intact",
                attempts[0].get("session_id") == "merge-test-session" if attempts else False,
            )
        )
        stability = payload.get("stability") or {}
        results.append(_ok("stability preserved", stability.get("promotion_confidence") == 88))
        promotions = payload.get("listening_official_promotions") or {}
        results.append(_ok("promotion history preserved", len(promotions.get("events") or []) == 1))
        results.append(_ok("unknown JSON key preserved", payload.get("custom_future_key", {}).get("version") == 1))
        results.append(_ok("readiness score updated", payload.get("readiness_score") == 55))
        results.append(_ok("column score updated", row.promotion_readiness_score == 55))

        await db.rollback()
    return results


async def verify_promotion_test_survives_lesson_submit() -> list[bool]:
    print("\n=== Promotion test survives lesson submit ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_progression(db)
        if ids is None:
            return [_ok("skip lesson submit (no progression row)", True)]

        sid, lid = ids
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
            source="verify_production_fix_pr_a",
            force=True,
        )
        row.promotion_readiness_json = _rich_json_payload(session_id="survive-lesson-session")
        await db.flush()

        await run_listening_progression_after_submit(db, student_id=sid, language_id=lid)
        await db.refresh(row)
        payload = row.promotion_readiness_json or {}
        attempts = (payload.get("listening_promotion_tests") or {}).get("attempts") or []

        results.append(_ok("attempts survive runtime pipeline", len(attempts) == 1))
        results.append(
            _ok(
                "PASS result intact after submit",
                attempts[0].get("result") == PromotionTestOutcome.PASS.value if attempts else False,
            )
        )
        results.append(_ok("custom key survives runtime", payload.get("custom_future_key") is not None))

        await db.rollback()
    return results


async def verify_backward_compat_old_readiness_only() -> list[bool]:
    print("\n=== Backward compat (readiness-only JSON) ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_progression(db)
        if ids is None:
            return [_ok("skip backward compat (no progression row)", True)]

        sid, lid = ids
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        row.promotion_readiness_json = {
            "skill": "listening",
            "official_cefr": "A1",
            "readiness_score": 10,
            "status": "NOT_READY",
        }
        await db.flush()

        await save_listening_promotion_readiness(
            db,
            student_id=sid,
            language_id=lid,
            result=_minimal_readiness_result(readiness_score=20, official_cefr="A1"),
        )
        await db.refresh(row)
        payload = row.promotion_readiness_json or {}
        results.append(_ok("readiness-only row still saves", payload.get("readiness_score") == 20))
        results.append(_ok("skill field present", payload.get("skill") == "listening"))
        results.append(_ok("no crash on missing buckets", "listening_promotion_tests" not in payload))

        await db.rollback()
    return results


async def verify_http_submit_persists() -> list[bool]:
    print("\n=== Promotion test submit persists (HTTP commit pattern) ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_progression(db)
        if ids is None:
            return [_ok("skip submit persist (no progression row)", True)]

        sid, lid = ids
        await clear_sessions_for_tests(db, student_id=sid, language_id=lid)
        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_production_fix_pr_a_submit",
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
        await db.commit()

    async with AsyncSessionLocal() as db:
        out = await submit_listening_promotion_test_api(
            db,
            student_id=sid,
            language_id=lid,
            session_id=session.session_id,
            answers=answers,
        )
        await db.commit()
        persisted_session_id = out.session_id

    async with AsyncSessionLocal() as db:
        state = await load_promotion_test_state(db, student_id=sid, language_id=lid)
        attempt = next(
            (a for a in (state.get("attempts") or []) if a.get("session_id") == persisted_session_id),
            None,
        )
        results.append(_ok("attempt visible in fresh session", attempt is not None))
        results.append(
            _ok(
                "attempt result persisted",
                attempt is not None and attempt.get("result") == out.result,
                str(attempt.get("result") if attempt else None),
            )
        )

        await db.execute(
            text(
                "DELETE FROM language_progression_events "
                "WHERE student_id = :sid AND language_id = :lid "
                "AND event_type = 'listening_promotion_test_completed' "
                "AND payload_json->>'session_id' = :sess"
            ),
            {"sid": sid, "lid": lid, "sess": persisted_session_id},
        )
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        if row and row.promotion_readiness_json:
            bucket = dict(row.promotion_readiness_json)
            tests = bucket.get("listening_promotion_tests") or {}
            tests["attempts"] = [
                a
                for a in (tests.get("attempts") or [])
                if str(a.get("session_id")) != persisted_session_id
            ]
            bucket["listening_promotion_tests"] = tests
            row.promotion_readiness_json = bucket
        await db.commit()

    return results


async def verify_http_promote_persists() -> list[bool]:
    print("\n=== Official promotion persists (HTTP commit pattern) ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_progression(db)
        if ids is None:
            return [_ok("skip promote persist (no progression row)", True)]

        sid, lid = ids
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
            source="verify_production_fix_pr_a_promote",
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
        breakdown, correct = grade_promotion_test_session(
            session, {a.assessment_id: a.correct_index for a in session.assessments}
        )
        result = build_promotion_test_result(session=session, breakdown=breakdown, correct_count=correct)
        await save_promotion_test_attempt(
            db, student_id=sid, language_id=lid, session=session, result=result
        )
        await db.commit()

    async with AsyncSessionLocal() as db:
        applied = await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
        await db.commit()
        new_cefr = applied.new_cefr

    async with AsyncSessionLocal() as db:
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        results.append(_ok("official CEFR persisted in fresh session", row.official_listening_cefr.value == new_cefr))
        results.append(_ok("promotion_success", applied.promotion_success))

        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_production_fix_pr_a_restore",
            force=True,
        )
        await db.commit()

    return results


def _function_body(source: str, name: str) -> str:
    marker = f"async def {name}("
    if marker not in source:
        return ""
    rest = source.split(marker, 1)[1]
    next_def = rest.find("\nasync def ")
    return rest if next_def < 0 else rest[:next_def]


def verify_route_commit_pattern() -> list[bool]:
    print("\n=== HTTP route commit pattern ===")
    results: list[bool] = []
    backend = Path(__file__).resolve().parents[1]
    promo_src = (backend / "app" / "api" / "language_promotion_test.py").read_text(encoding="utf-8")
    official_src = (backend / "app" / "api" / "language_official_promotion.py").read_text(encoding="utf-8")
    storage_src = (
        backend / "app" / "services" / "language_promotion_readiness" / "storage.py"
    ).read_text(encoding="utf-8")

    submit_body = _function_body(promo_src, "promotion_test_submit")
    start_body = _function_body(promo_src, "promotion_test_start")
    status_body = _function_body(promo_src, "promotion_test_status")
    promote_body = _function_body(official_src, "listening_official_promote")

    results.append(_ok("submit route commits", "await db.commit()" in submit_body))
    results.append(_ok("start route commits persisted session", "await db.commit()" in start_body))
    results.append(_ok("status route does not commit", "await db.commit()" not in status_body))
    results.append(_ok("promote route commits", "await db.commit()" in promote_body))
    results.append(_ok("storage uses merge update", "payload.update(" in storage_src))
    return results


async def run_regression() -> list[bool]:
    print("\n=== Regression scripts ===")
    import subprocess

    scripts = [
        "verify_language_promotion_test_phase_5_4.py",
        "verify_language_official_promotion_phase_5_5.py",
        "verify_language_listening_progression_runtime_pr_1.py",
    ]
    results: list[bool] = []
    backend = Path(__file__).resolve().parents[1]
    for script in scripts:
        proc = subprocess.run(
            [sys.executable, str(backend / "scripts" / script)],
            cwd=str(backend),
            capture_output=True,
            text=True,
        )
        passed = proc.returncode == 0 and "PASS" in (proc.stdout or "")
        results.append(_ok(f"regression {script}", passed))
        if not passed:
            print(proc.stdout[-500:] if proc.stdout else proc.stderr[-500:])
    return results


async def main() -> int:
    print("verify_language_production_fix_pr_a")
    all_results: list[bool] = []
    all_results.extend(await verify_readiness_merge_preserves_buckets())
    all_results.extend(await verify_promotion_test_survives_lesson_submit())
    all_results.extend(await verify_backward_compat_old_readiness_only())
    all_results.extend(await verify_http_submit_persists())
    all_results.extend(await verify_http_promote_persists())
    all_results.extend(verify_route_commit_pattern())
    all_results.extend(await run_regression())

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
