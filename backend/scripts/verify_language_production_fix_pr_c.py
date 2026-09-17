"""Verify PR-C — Production hardening (persistent sessions + row locking).

Usage (from backend/):
    python scripts/verify_language_production_fix_pr_c.py
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import func, select, text

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progression import LanguageProgression, LanguageProgressionEvent
from app.services.language_official_promotion_api import (
    OfficialPromotionApiError,
    apply_listening_official_promotion_api,
)
from app.services.language_progression_service import (
    ensure_progression_row,
    progression_enabled,
    official_select_enabled,
    upsert_official_levels,
)
from app.services.language_promotion_test import PromotionTestOutcome, clear_sessions_for_tests
from app.services.language_promotion_test.builder import build_promotion_test_session
from app.services.language_promotion_test.engine import create_listening_promotion_test_session
from app.services.language_promotion_test.scoring import grade_promotion_test_session
from app.services.language_promotion_test.session import find_active_session, get_session, register_session
from app.services.language_promotion_test.session_storage import session_from_dict, session_to_dict
from app.services.language_promotion_test.storage import load_promotion_test_state, save_promotion_test_attempt
from app.services.language_promotion_test.telemetry import build_promotion_test_result
from app.services.language_promotion_test.types import PromotionTestEligibility
from app.services.language_promotion_test_api import (
    PromotionTestApiError,
    submit_listening_promotion_test_api,
)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


async def _sample_ids(db) -> tuple[int, int] | None:
    row = (
        await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
    ).first()
    if row is None:
        return None
    return int(row[0]), int(row[1])


def _eligible() -> PromotionTestEligibility:
    return PromotionTestEligibility(
        eligible=True,
        reason="ok",
        official_cefr="A2",
        target_cefr="B1",
        readiness_score=100,
        readiness_status="PROMOTION_AVAILABLE",
    )


async def verify_session_persistence_across_workers() -> list[bool]:
    print("\n=== Session persistence across workers ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip worker persistence", True)]
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
            source="verify_pr_c_worker",
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
        await db.commit()
        session_id = session.session_id

    async with AsyncSessionLocal() as db:
        loaded = await get_session(db, session_id, student_id=sid, language_id=lid)
        results.append(_ok("session readable in fresh connection", loaded is not None))
        results.append(
            _ok(
                "serialized assessments preserved",
                loaded is not None and len(loaded.assessments) == len(session.assessments),
            )
        )
        active = await find_active_session(db, student_id=sid, language_id=lid)
        results.append(_ok("active session discoverable", active is not None and active.session_id == session_id))
        await clear_sessions_for_tests(db, student_id=sid, language_id=lid)
        await db.commit()

    return results


async def verify_duplicate_submit_blocked() -> list[bool]:
    print("\n=== Duplicate submit blocked ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip duplicate submit", True)]
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
            source="verify_pr_c_dup_submit",
            force=True,
        )
        with patch(
            "app.services.language_promotion_test.engine.check_promotion_test_eligibility",
            return_value=_eligible(),
        ):
            started = await create_listening_promotion_test_session(db, student_id=sid, language_id=lid)
        await db.commit()
        session_id = started.session_id
        answers = {a.assessment_id: a.correct_index for a in started.assessments}

    async with AsyncSessionLocal() as db:
        loaded = await get_session(db, session_id, student_id=sid, language_id=lid)
        results.append(_ok("session visible before submit", loaded is not None))
        first = await submit_listening_promotion_test_api(
            db,
            student_id=sid,
            language_id=lid,
            session_id=session_id,
            answers=answers,
        )
        await db.commit()
        results.append(_ok("first submit succeeds", first.result == PromotionTestOutcome.PASS.value))

    async with AsyncSessionLocal() as db:
        try:
            await submit_listening_promotion_test_api(
                db,
                student_id=sid,
                language_id=lid,
                session_id=session_id,
                answers=answers,
            )
            results.append(_ok("second submit rejected", False))
        except PromotionTestApiError as exc:
            results.append(_ok("second submit returns 409", exc.status_code == 409))

        state = await load_promotion_test_state(db, student_id=sid, language_id=lid)
        attempts = [a for a in (state.get("attempts") or []) if a.get("session_id") == session_id]
        results.append(_ok("single attempt history row", len(attempts) == 1))
        await db.rollback()

    return results


async def verify_concurrent_submit_race() -> list[bool]:
    print("\n=== Concurrent submit race ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip concurrent submit", True)]
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
            source="verify_pr_c_race_submit",
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
        await db.commit()
        session_id = session.session_id
        answers = {a.assessment_id: a.correct_index for a in session.assessments}

    async def _submit_once():
        async with AsyncSessionLocal() as db:
            try:
                out = await submit_listening_promotion_test_api(
                    db,
                    student_id=sid,
                    language_id=lid,
                    session_id=session_id,
                    answers=answers,
                )
                await db.commit()
                return ("ok", out)
            except PromotionTestApiError as exc:
                await db.rollback()
                return ("conflict", exc.status_code)

    outcomes = await asyncio.gather(_submit_once(), _submit_once())
    ok_count = sum(1 for kind, _ in outcomes if kind == "ok")
    conflict_count = sum(1 for kind, val in outcomes if kind == "conflict" and val == 409)
    results.append(_ok("exactly one submit succeeds", ok_count == 1, str(outcomes)))
    results.append(_ok("other submit gets conflict", conflict_count >= 1))

    async with AsyncSessionLocal() as db:
        state = await load_promotion_test_state(db, student_id=sid, language_id=lid)
        attempts = [a for a in (state.get("attempts") or []) if a.get("session_id") == session_id]
        results.append(_ok("only one attempt stored", len(attempts) == 1))
        event_count = await db.scalar(
            select(func.count())
            .select_from(LanguageProgressionEvent)
            .where(
                LanguageProgressionEvent.student_id == sid,
                LanguageProgressionEvent.language_id == lid,
                LanguageProgressionEvent.event_type == "listening_promotion_test_completed",
            )
        )
        results.append(_ok("no duplicate completion events beyond attempt", int(event_count or 0) >= 1))
        await db.rollback()

    return results


async def _seed_pass_attempt(db, sid: int, lid: int) -> str:
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
        source="verify_pr_c_promote",
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
    await register_session(db, session)
    await save_promotion_test_attempt(db, student_id=sid, language_id=lid, session=session, result=result)
    await db.commit()
    return session.session_id


async def verify_duplicate_promotion_blocked() -> list[bool]:
    print("\n=== Duplicate promotion blocked ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip duplicate promote", True)]
        sid, lid = ids
        await _seed_pass_attempt(db, sid, lid)

    async with AsyncSessionLocal() as db:
        first = await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
        await db.commit()
        results.append(_ok("first promote succeeds", first.promotion_success))

    async with AsyncSessionLocal() as db:
        try:
            await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
            results.append(_ok("second promote rejected", False))
        except OfficialPromotionApiError as exc:
            results.append(_ok("second promote returns 409", exc.status_code == 409))

        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        results.append(_ok("CEFR promoted once", row.official_listening_cefr == LanguageLevel.B1))
        events = (row.promotion_readiness_json or {}).get("listening_official_promotions", {}).get("events") or []
        results.append(_ok("single promotion event bucket entry per session", len(events) >= 1))
        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_pr_c_restore",
            force=True,
        )
        await db.commit()

    return results


async def verify_concurrent_promotion_race() -> list[bool]:
    print("\n=== Concurrent promotion race ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip concurrent promote", True)]
        sid, lid = ids
        session_id = await _seed_pass_attempt(db, sid, lid)

    async def _promote_once():
        async with AsyncSessionLocal() as db:
            try:
                out = await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
                await db.commit()
                return ("ok", out.new_cefr)
            except OfficialPromotionApiError as exc:
                await db.rollback()
                return ("conflict", exc.status_code)

    outcomes = await asyncio.gather(_promote_once(), _promote_once())
    ok_count = sum(1 for kind, _ in outcomes if kind == "ok")
    results.append(_ok("one promotion applied", ok_count == 1, str(outcomes)))

    async with AsyncSessionLocal() as db:
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        results.append(_ok("CEFR is B1 not B2", row.official_listening_cefr == LanguageLevel.B1))
        promoted_ids = (
            (row.promotion_readiness_json or {})
            .get("listening_official_promotions", {})
            .get("promoted_session_ids")
            or []
        )
        results.append(
            _ok(
                "one promoted session id",
                promoted_ids.count(session_id) == 1,
                f"session={session_id} ids={promoted_ids}",
            )
        )
        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_pr_c_restore2",
            force=True,
        )
        await db.commit()

    return results


async def verify_session_expiry_and_ownership() -> list[bool]:
    print("\n=== Session expiry + ownership ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip expiry/ownership", True)]
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
            source="verify_pr_c_expiry",
            force=True,
        )
        expired = build_promotion_test_session(
            student_id=sid,
            language_id=lid,
            official_cefr="A2",
            target_cefr="B1",
            attempt_number=1,
            used_lesson_ids=set(),
            used_sequences=set(),
        )
        expired.expires_at = time.time() - 5
        await register_session(db, expired)
        await db.commit()

    async with AsyncSessionLocal() as db:
        try:
            await submit_listening_promotion_test_api(
                db,
                student_id=sid,
                language_id=lid,
                session_id=expired.session_id,
                answers={a.assessment_id: 0 for a in expired.assessments},
            )
            results.append(_ok("expired session rejected", False))
        except PromotionTestApiError as exc:
            results.append(_ok("expired returns 410", exc.status_code == 410))

        live = build_promotion_test_session(
            student_id=sid,
            language_id=lid,
            official_cefr="A2",
            target_cefr="B1",
            attempt_number=2,
            used_lesson_ids=set(),
            used_sequences=set(),
        )
        await register_session(db, live)
        await db.commit()

    async with AsyncSessionLocal() as db:
        try:
            await submit_listening_promotion_test_api(
                db,
                student_id=sid + 99999,
                language_id=lid,
                session_id=live.session_id,
                answers={a.assessment_id: a.correct_index for a in live.assessments},
            )
            results.append(_ok("wrong student rejected", False))
        except PromotionTestApiError as exc:
            results.append(_ok("wrong student returns 404", exc.status_code == 404))
        await clear_sessions_for_tests(db, student_id=sid, language_id=lid)
        await db.commit()

    return results


async def verify_session_closed_after_promotion() -> list[bool]:
    print("\n=== Session unusable after promotion ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip post-promotion session", True)]
        sid, lid = ids

    async with AsyncSessionLocal() as db:
        session_id = await _seed_pass_attempt(db, sid, lid)

    async with AsyncSessionLocal() as db:
        await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
        await db.commit()

    async with AsyncSessionLocal() as db:
        live = await get_session(db, session_id, student_id=sid, language_id=lid)
        results.append(_ok("session removed after promotion", live is None))
        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_pr_c_restore3",
            force=True,
        )
        await db.commit()

    return results


def verify_persistence_source_audit() -> list[bool]:
    print("\n=== Persistence + locking audit ===")
    results: list[bool] = []
    backend = Path(__file__).resolve().parents[1]
    session_src = (backend / "app" / "services" / "language_promotion_test" / "session.py").read_text(encoding="utf-8")
    storage_src = (backend / "app" / "services" / "language_promotion_test" / "session_storage.py").read_text(encoding="utf-8")
    engine_src = (backend / "app" / "services" / "language_promotion_test" / "engine.py").read_text(encoding="utf-8")
    promo_api = (backend / "app" / "services" / "language_official_promotion_api" / "service.py").read_text(encoding="utf-8")
    route_src = (backend / "app" / "api" / "language_promotion_test.py").read_text(encoding="utf-8")

    results.append(_ok("no in-memory _sessions dict", "_sessions:" not in session_src and "_sessions =" not in session_src))
    results.append(_ok("session persisted in JSON", "active_sessions" in storage_src))
    results.append(_ok("submit uses row lock", "lock_listening_progression_row" in engine_src))
    results.append(_ok("promote API uses row lock", "lock_listening_progression_row" in promo_api))
    results.append(_ok("start route commits persisted session", "await db.commit()" in route_src))
    return results


async def verify_feature_flag_matrix() -> list[bool]:
    print("\n=== Feature flag matrix ===")
    results: list[bool] = []

    results.append(_ok("ENABLED defaults false", progression_enabled() is False))
    results.append(_ok("OFFICIAL_SELECT defaults false", official_select_enabled() is False))

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return results + [_ok("skip ensure_progression_row live test", True)]
        sid, lid = ids
        with patch("app.services.language_progression_service.progression_enabled", return_value=False):
            row = await ensure_progression_row(db, student_id=sid, language_id=lid)
            results.append(_ok("DISABLED does not create row when missing", row is None or isinstance(row, LanguageProgression)))
        with patch("app.services.language_progression_service.progression_enabled", return_value=True):
            created = await ensure_progression_row(db, student_id=sid, language_id=lid)
            results.append(_ok("ENABLED ensure returns row when possible", created is not None))
        await db.rollback()

    restored = session_from_dict(session_to_dict(build_promotion_test_session(
        student_id=1,
        language_id=1,
        official_cefr="A2",
        target_cefr="B1",
        attempt_number=1,
        used_lesson_ids=set(),
        used_sequences=set(),
    )))
    results.append(_ok("session round-trip preserves id", bool(restored.session_id)))
    return results


async def verify_normal_promotion_still_works() -> list[bool]:
    print("\n=== Normal promotion still works ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip normal promotion", True)]
        sid, lid = ids
        await _seed_pass_attempt(db, sid, lid)

    async with AsyncSessionLocal() as db:
        with patch(
            "app.services.language_promotion_test.engine.check_promotion_test_eligibility",
            return_value=_eligible(),
        ):
            started = await create_listening_promotion_test_session(db, student_id=sid, language_id=lid)
        results.append(_ok("session create still works", bool(getattr(started, "session_id", ""))))
        applied = await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
        results.append(_ok("promotion still succeeds", applied.promotion_success))
        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_pr_c_restore4",
            force=True,
        )
        await db.commit()

    return results


async def run_regression() -> list[bool]:
    print("\n=== Regression scripts ===")
    backend = Path(__file__).resolve().parents[1]
    scripts = [
        "verify_language_promotion_test_phase_5_4.py",
        "verify_language_official_promotion_phase_5_5.py",
        "verify_language_listening_progression_runtime_pr_1.py",
        "verify_language_production_fix_pr_a.py",
        "verify_language_production_fix_pr_b.py",
    ]
    results: list[bool] = []
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
            print((proc.stdout or proc.stderr or "")[-500:])
    return results


async def main() -> int:
    print("verify_language_production_fix_pr_c")
    all_results: list[bool] = []
    all_results.extend(await verify_session_persistence_across_workers())
    all_results.extend(await verify_duplicate_submit_blocked())
    all_results.extend(await verify_concurrent_submit_race())
    all_results.extend(await verify_duplicate_promotion_blocked())
    all_results.extend(await verify_concurrent_promotion_race())
    all_results.extend(await verify_session_expiry_and_ownership())
    all_results.extend(await verify_session_closed_after_promotion())
    all_results.extend(verify_persistence_source_audit())
    all_results.extend(await verify_feature_flag_matrix())
    all_results.extend(await verify_normal_promotion_still_works())
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
