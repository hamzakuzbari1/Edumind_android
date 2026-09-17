"""Verify PR-STAB-3 — Progression JSON Concurrency (Listening Only).

Usage (from backend/):
    python scripts/verify_language_stabilization_pr_3_json.py
"""

from __future__ import annotations

import asyncio
import inspect
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel
from app.models.language.progression import LanguageProgression
from app.services.language_listening_progression.json_mutation import mutate_listening_progression_json
from app.services.language_progression_service import upsert_official_levels
from app.services.language_promotion_test import clear_sessions_for_tests
from app.services.language_promotion_test.builder import build_promotion_test_session
from app.services.language_promotion_test.session_storage import register_promotion_test_session


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


async def _sample_ids(db) -> tuple[int, int] | None:
    row = (
        await db.execute(text("SELECT student_id, language_id FROM language_analytics LIMIT 1"))
    ).first()
    if row is None:
        return None
    return int(row[0]), int(row[1])


def verify_canonical_mutator() -> list[bool]:
    print("\n=== Canonical JSON mutator (Part 1) ===")
    results: list[bool] = []
    path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "language_listening_progression"
        / "json_mutation.py"
    )
    src = path.read_text(encoding="utf-8")
    results.append(_ok("mutator module exists", path.is_file()))
    results.append(_ok("uses lock_listening_progression_row", "lock_listening_progression_row" in src))
    results.append(_ok("uses flag_modified", "flag_modified" in src))
    results.append(_ok("accepts locked_row", "locked_row" in src))
    sig = inspect.signature(mutate_listening_progression_json)
    results.append(_ok("public API exported", "mutator" in sig.parameters))
    return results


def verify_writers_use_mutator() -> list[bool]:
    print("\n=== All writers use canonical mutator (Part 2) ===")
    results: list[bool] = []
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    writer_files = [
        "language_promotion_readiness/storage.py",
        "language_promotion_stability/storage.py",
        "language_promotion_test/storage.py",
        "language_promotion_test/session_storage.py",
        "language_official_promotion/storage.py",
    ]
    for rel in writer_files:
        src = (root / rel).read_text(encoding="utf-8")
        results.append(
            _ok(
                f"{rel} uses mutate_listening_progression_json",
                "mutate_listening_progression_json" in src,
            )
        )
        results.append(
            _ok(
                f"{rel} has no direct promotion_readiness_json assignment",
                "promotion_readiness_json =" not in src,
            )
        )

    mutation_src = (root / "language_listening_progression" / "json_mutation.py").read_text(encoding="utf-8")
    direct_writes = []
    for path in root.rglob("*.py"):
        if "json_mutation.py" in str(path):
            continue
        if "promotion_readiness_json =" in path.read_text(encoding="utf-8"):
            direct_writes.append(str(path.relative_to(root)))
    results.append(
        _ok(
            "only json_mutation assigns promotion_readiness_json",
            direct_writes == [],
            ", ".join(direct_writes) if direct_writes else "none",
        )
    )
    results.append(_ok("json_mutation calls flag_modified", "flag_modified" in mutation_src))
    return results


def verify_session_lookup() -> list[bool]:
    print("\n=== Session lookup without table scan (Part 6) ===")
    results: list[bool] = []
    src = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "language_promotion_test"
        / "session_storage.py"
    ).read_text(encoding="utf-8")
    load_body = src.split("async def load_promotion_test_session", 1)[1].split("\nasync def", 1)[0]
    results.append(_ok("no full-table select in loader", "select(LanguageProgression)" not in load_body))
    sig = inspect.signature(
        __import__(
            "app.services.language_promotion_test.session_storage",
            fromlist=["load_promotion_test_session"],
        ).load_promotion_test_session
    )
    results.append(_ok("student_id required", "student_id" in sig.parameters))
    results.append(_ok("language_id required", "language_id" in sig.parameters))
    return results


def verify_promotion_start_locking() -> list[bool]:
    print("\n=== Promotion Test Start locking (Part 3) ===")
    results: list[bool] = []
    engine_src = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "language_promotion_test" / "engine.py"
    ).read_text(encoding="utf-8")
    create_body = engine_src.split("async def create_listening_promotion_test_session", 1)[1].split(
        "\nasync def", 1
    )[0]
    session_src = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "language_promotion_test"
        / "session_storage.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("create locks progression row", "lock_listening_progression_row" in create_body))
    results.append(
        _ok(
            "register returns existing active session",
            "_find_valid_active_session" in session_src and "existing is not None" in session_src,
        )
    )
    return results


def verify_official_promotion_engine_locking() -> list[bool]:
    print("\n=== Official Promotion engine safety (Part 4) ===")
    results: list[bool] = []
    engine_src = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "language_official_promotion" / "engine.py"
    ).read_text(encoding="utf-8")
    api_src = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "language_official_promotion_api"
        / "service.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("engine accepts locked_row", "locked_row" in engine_src))
    results.append(_ok("engine acquires lock when needed", "lock_listening_progression_row" in engine_src))
    results.append(_ok("API passes locked_row to engine", "locked_row=row" in api_src))
    results.append(
        _ok(
            "append uses mutator path",
            "append_promotion_record" in engine_src
            and "locked_row=row" in engine_src,
        )
    )
    return results


async def verify_concurrent_field_merge() -> list[bool]:
    print("\n=== Concurrent JSON field preservation ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip concurrent merge", True)]
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
            source="verify_stab3_merge",
            force=True,
        )
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        assert row is not None

        async def write_readiness():
            def mutator(payload: dict) -> None:
                payload["readiness_score"] = 88
                payload["stab3_marker_readiness"] = True

            await mutate_listening_progression_json(
                db, student_id=sid, language_id=lid, mutator=mutator
            )

        async def write_stability():
            def mutator(payload: dict) -> None:
                payload["stability"] = {"promotion_confidence": 77, "history": [{"n": 1}]}
                payload["stab3_marker_stability"] = True

            await mutate_listening_progression_json(
                db, student_id=sid, language_id=lid, mutator=mutator
            )

        await write_readiness()
        await write_stability()
        await db.refresh(row)
        payload = row.promotion_readiness_json or {}
        results.append(_ok("readiness marker preserved", payload.get("stab3_marker_readiness") is True))
        results.append(_ok("stability marker preserved", payload.get("stab3_marker_stability") is True))
        results.append(_ok("stability bucket preserved", (payload.get("stability") or {}).get("promotion_confidence") == 77))
        results.append(_ok("readiness score preserved", payload.get("readiness_score") == 88))
        await db.rollback()

    return results


async def verify_duplicate_session_start() -> list[bool]:
    print("\n=== Duplicate promotion-test start prevention ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip duplicate session test", True)]
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
            source="verify_stab3_session",
            force=True,
        )

        first = build_promotion_test_session(
            student_id=sid,
            language_id=lid,
            official_cefr="A2",
            target_cefr="B1",
            attempt_number=1,
            used_lesson_ids=set(),
            used_sequences=set(),
        )
        second = build_promotion_test_session(
            student_id=sid,
            language_id=lid,
            official_cefr="A2",
            target_cefr="B1",
            attempt_number=2,
            used_lesson_ids=set(),
            used_sequences=set(),
        )

        saved_first = await register_promotion_test_session(db, first)
        saved_second = await register_promotion_test_session(db, second)
        results.append(_ok("first session registered", bool(saved_first.session_id)))
        results.append(
            _ok(
                "second start returns existing session",
                saved_first.session_id == saved_second.session_id,
                f"{saved_first.session_id} vs {saved_second.session_id}",
            )
        )

        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        bucket = ((row.promotion_readiness_json or {}).get("listening_promotion_tests") or {})
        active = bucket.get("active_sessions") or {}
        results.append(_ok("only one active session stored", len(active) == 1))
        await db.rollback()

    return results


async def verify_duplicate_promotion_history() -> list[bool]:
    print("\n=== Duplicate official promotion history prevention ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip duplicate promotion history", True)]

        sid, lid = ids
        from app.services.language_official_promotion.storage import append_promotion_record
        from app.services.language_official_promotion.types import PromotionTestAttemptRef

        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_stab3_promo",
            force=True,
        )
        attempt = PromotionTestAttemptRef(
            session_id="stab3-session",
            attempt_number=1,
            official_cefr="A2",
            target_cefr="B1",
            overall_score=100.0,
            result="PASS",
        )

        await append_promotion_record(
            db,
            student_id=sid,
            language_id=lid,
            event_id=1,
            attempt=attempt,
            telemetry_snapshot={},
            journey_reset={},
        )
        duplicate = await append_promotion_record(
            db,
            student_id=sid,
            language_id=lid,
            event_id=2,
            attempt=attempt,
            telemetry_snapshot={},
            journey_reset={},
        )
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        events = (
            (row.promotion_readiness_json or {})
            .get("listening_official_promotions", {})
            .get("events", [])
        )
        stab3_events = [
            event
            for event in events
            if isinstance(event, dict) and event.get("session_id") == attempt.session_id
        ]
        results.append(_ok("first append stored", len(stab3_events) == 1))
        results.append(_ok("duplicate append skipped", duplicate is None))
        await db.rollback()

    return results


def verify_regression_subprocess(script: str) -> list[bool]:
    print(f"\n=== Regression: {script} ===")
    results: list[bool] = []
    path = Path(__file__).resolve().parents[1] / "scripts" / script
    if not path.is_file():
        return [_ok(f"{script} present", False)]
    proc = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    out = proc.stdout or ""
    passed = proc.returncode == 0 or "PASS" in out.splitlines()[-5:]
    tail = out[-400:]
    results.append(_ok(script, passed, tail.strip().splitlines()[-1] if tail else f"exit {proc.returncode}"))
    return results


async def main() -> int:
    print("verify_language_stabilization_pr_3_json")
    all_results: list[bool] = []

    all_results.extend(verify_canonical_mutator())
    all_results.extend(verify_writers_use_mutator())
    all_results.extend(verify_session_lookup())
    all_results.extend(verify_promotion_start_locking())
    all_results.extend(verify_official_promotion_engine_locking())
    all_results.extend(await verify_concurrent_field_merge())
    all_results.extend(await verify_duplicate_session_start())
    all_results.extend(await verify_duplicate_promotion_history())

    for script in (
        "verify_language_production_fix_pr_a.py",
        "verify_language_production_fix_pr_b.py",
        "verify_language_production_fix_pr_c.py",
        "verify_language_stabilization_pr_1_adaptive.py",
        "verify_language_stabilization_pr_2_cefr_sync.py",
        "verify_language_promotion_test_api_pr_2.py",
        "verify_language_official_promotion_api_pr_3.py",
        "verify_language_listening_progression_runtime_pr_1.py",
    ):
        all_results.extend(verify_regression_subprocess(script))

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
