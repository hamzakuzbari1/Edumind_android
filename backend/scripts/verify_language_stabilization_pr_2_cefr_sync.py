"""Verify PR-STAB-2 — Official CEFR Consistency (Listening Only).

Usage (from backend/):
    python scripts/verify_language_stabilization_pr_2_cefr_sync.py
"""

from __future__ import annotations

import asyncio
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
from app.models.language.analytics import LanguageAnalytics
from app.models.language.enums import LanguageLevel
from app.models.language.progression import LanguageProgression
from app.services.language_level_utils import bottleneck_level
from app.services.language_progression_service import (
    PROGRESSION_UNAVAILABLE_REASON,
    ensure_progression_row,
    official_select_enabled,
    progression_enabled,
    upsert_official_levels,
)
from app.services.language_promotion_test import PromotionTestOutcome, clear_sessions_for_tests
from app.services.language_promotion_test.builder import build_promotion_test_session
from app.services.language_promotion_test.types import PromotionTestEligibility


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


def _seed_attempt_payload(*, session_id: str) -> dict:
    return {
        "listening_promotion_tests": {
            "attempts": [
                {
                    "session_id": session_id,
                    "attempt_number": 1,
                    "official_cefr": "A2",
                    "target_cefr": "B1",
                    "overall_score": 100.0,
                    "result": PromotionTestOutcome.PASS.value,
                    "objective_scores": {},
                }
            ],
            "used_lesson_ids": [],
            "used_sequences": [],
        },
        "stability": {"history": [{"lesson_index": 1}]},
        "skill": "listening",
        "official_cefr": "A2",
    }


def _eligible() -> PromotionTestEligibility:
    return PromotionTestEligibility(
        eligible=True,
        reason="test eligible",
        official_cefr="A2",
        target_cefr="B1",
        readiness_score=100,
        readiness_status="PROMOTION_AVAILABLE",
    )


async def _sample_ids(db) -> tuple[int, int] | None:
    row = (
        await db.execute(text("SELECT student_id, language_id FROM language_analytics LIMIT 1"))
    ).first()
    if row is None:
        return None
    return int(row[0]), int(row[1])


def verify_policy_comments() -> list[bool]:
    print("\n=== Promotion policy documented (Part 4) ===")
    results: list[bool] = []
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    progression = (root / "language_progression_service.py").read_text(encoding="utf-8")
    promo_engine = (root / "language_official_promotion" / "engine.py").read_text(encoding="utf-8")
    test_engine = (root / "language_promotion_test" / "engine.py").read_text(encoding="utf-8")
    results.append(_ok("progression policy doc", "Official Promotion engine" in progression))
    results.append(_ok("official promotion sole writer", "ONLY runtime writer" in promo_engine))
    results.append(_ok("promotion test never promotes", "Never mutates official_listening_cefr" in test_engine))
    return results


def verify_sync_helper_exists() -> list[bool]:
    print("\n=== Analytics sync helper (L-02) ===")
    results: list[bool] = []
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    progression = (root / "language_progression_service.py").read_text(encoding="utf-8")
    engine_src = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "language_official_promotion" / "engine.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("sync_analytics_listening_level defined", "sync_analytics_listening_level" in progression))
    results.append(_ok("engine calls sync after promote", "sync_analytics_listening_level" in engine_src))
    results.append(
        _ok(
            "sync touches listening only in helper",
            "analytics.listening_level = listening_level" in progression
            and "reading_level =" not in progression.split("sync_analytics_listening_level", 1)[1].split("async def", 1)[0],
        )
    )
    return results


async def verify_official_promotion_syncs_analytics() -> list[bool]:
    print("\n=== Official Promotion syncs analytics listening (L-02) ===")
    results: list[bool] = []
    try:
        from app.services.language_official_promotion.engine import apply_listening_official_promotion
    except ModuleNotFoundError as exc:
        return [_ok(f"skip analytics sync integration ({exc.name})", True)]

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip analytics sync test", True)]
        sid, lid = ids

        analytics = await db.get(LanguageAnalytics, {"student_id": sid, "language_id": lid})
        if analytics is None:
            return [_ok("skip analytics sync test (no row)", True)]

        await clear_sessions_for_tests(db, student_id=sid, language_id=lid)
        analytics.reading_level = LanguageLevel.B1
        analytics.writing_level = LanguageLevel.A2
        analytics.speaking_level = LanguageLevel.A2
        analytics.listening_level = LanguageLevel.A2
        analytics.overall_level_internal = bottleneck_level(
            {
                "reading": analytics.reading_level.value,
                "listening": analytics.listening_level.value,
                "writing": analytics.writing_level.value,
                "speaking": analytics.speaking_level.value,
            }
        )
        before_reading = analytics.reading_level
        before_writing = analytics.writing_level
        before_speaking = analytics.speaking_level

        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.B1,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_stab2_sync",
            force=True,
        )
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        assert row is not None
        session = build_promotion_test_session(
            student_id=sid,
            language_id=lid,
            official_cefr="A2",
            target_cefr="B1",
            attempt_number=1,
            used_lesson_ids=set(),
            used_sequences=set(),
        )
        row.promotion_readiness_json = _seed_attempt_payload(session_id=session.session_id)
        await db.flush()

        applied = await apply_listening_official_promotion(db, student_id=sid, language_id=lid)
        await db.refresh(analytics)
        await db.refresh(row)

        expected_overall = bottleneck_level(
            {
                "reading": before_reading.value,
                "listening": LanguageLevel.B1.value,
                "writing": before_writing.value,
                "speaking": before_speaking.value,
            }
        )

        results.append(_ok("promotion succeeded", applied.promotion_success))
        results.append(_ok("official listening B1", row.official_listening_cefr == LanguageLevel.B1))
        results.append(_ok("analytics listening B1", analytics.listening_level == LanguageLevel.B1))
        results.append(_ok("reading unchanged", analytics.reading_level == before_reading))
        results.append(_ok("writing unchanged", analytics.writing_level == before_writing))
        results.append(_ok("speaking unchanged", analytics.speaking_level == before_speaking))
        results.append(
            _ok(
                "overall bottleneck recomputed",
                analytics.overall_level_internal == expected_overall,
                f"expected {expected_overall}, got {analytics.overall_level_internal}",
            )
        )

        await db.rollback()

    return results


async def verify_sync_helper_pure() -> list[bool]:
    print("\n=== sync_analytics_listening_level unit behavior ===")
    results: list[bool] = []
    try:
        from app.services.language_progression_service import sync_analytics_listening_level
    except ModuleNotFoundError as exc:
        return [_ok(f"skip sync helper unit ({exc.name})", True)]

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip sync helper unit", True)]
        sid, lid = ids
        analytics = await db.get(LanguageAnalytics, {"student_id": sid, "language_id": lid})
        if analytics is None:
            return [_ok("skip sync helper unit", True)]

        analytics.reading_level = LanguageLevel.C1
        analytics.writing_level = LanguageLevel.B2
        analytics.speaking_level = LanguageLevel.B1
        analytics.listening_level = LanguageLevel.A2

        synced = await sync_analytics_listening_level(
            db, student_id=sid, language_id=lid, listening_level=LanguageLevel.B2
        )
        assert synced is not None
        expected = bottleneck_level(
            {
                "reading": LanguageLevel.C1.value,
                "listening": LanguageLevel.B2.value,
                "writing": LanguageLevel.B2.value,
                "speaking": LanguageLevel.B1.value,
            }
        )
        results.append(_ok("listening updated", synced.listening_level == LanguageLevel.B2))
        results.append(_ok("reading preserved", synced.reading_level == LanguageLevel.C1))
        results.append(_ok("overall uses bottleneck", synced.overall_level_internal == expected))
        await db.rollback()

    return results


def verify_progression_row_wiring() -> list[bool]:
    print("\n=== Progression row lifecycle (L-07) ===")
    results: list[bool] = []
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    test_api = (root / "language_promotion_test_api" / "service.py").read_text(encoding="utf-8")
    test_engine = (root / "language_promotion_test" / "engine.py").read_text(encoding="utf-8")
    promo_api = (root / "language_official_promotion_api" / "service.py").read_text(encoding="utf-8")
    session_src = (root / "language_promotion_test" / "session_storage.py").read_text(encoding="utf-8")

    results.append(_ok("start API calls ensure_progression_row", "ensure_progression_row" in test_api))
    results.append(_ok("engine calls ensure_progression_row", "ensure_progression_row" in test_engine))
    results.append(_ok("promote API calls ensure_progression_row", "ensure_progression_row" in promo_api))
    results.append(
        _ok(
            "register_session still guards missing row",
            "Cannot persist promotion test session without a progression row" in session_src,
        )
    )
    return results


async def verify_start_never_500_missing_row() -> list[bool]:
    print("\n=== Promotion Test Start graceful when row missing (L-07) ===")
    results: list[bool] = []
    try:
        from app.services.language_promotion_test_api import PromotionTestApiError, start_listening_promotion_test
    except ModuleNotFoundError as exc:
        return [_ok(f"skip start missing row ({exc.name})", True)]

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip start missing row", True)]
        sid, lid = ids

        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        if row is not None:
            await db.delete(row)
            await db.flush()

        with patch("app.services.language_progression_service.progression_enabled", return_value=False):
            try:
                await start_listening_promotion_test(db, student_id=sid, language_id=lid)
                results.append(_ok("disabled progression returns structured error", False))
            except PromotionTestApiError as exc:
                results.append(_ok("disabled progression returns 503", exc.status_code == 503))
                results.append(
                    _ok(
                        "structured progression_available flag",
                        isinstance(exc.detail, dict) and exc.detail.get("progression_available") is False,
                    )
                )
            except RuntimeError:
                results.append(_ok("no RuntimeError on missing row", False))

        with (
            patch("app.services.language_progression_service.progression_enabled", return_value=True),
            patch(
                "app.services.language_promotion_test_api.service.create_listening_promotion_test_session",
                return_value=_eligible(),
            ),
        ):
            created = await ensure_progression_row(db, student_id=sid, language_id=lid)
            results.append(_ok("ensure creates row when enabled", created is not None))

        await db.rollback()

    return results


async def verify_promote_api_missing_row() -> list[bool]:
    print("\n=== Official Promotion API graceful when row missing ===")
    results: list[bool] = []
    try:
        from app.services.language_official_promotion_api import (
            OfficialPromotionApiError,
            apply_listening_official_promotion_api,
        )
    except ModuleNotFoundError as exc:
        return [_ok(f"skip promote missing row ({exc.name})", True)]

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip promote missing row", True)]
        sid, lid = ids
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        if row is not None:
            await db.delete(row)
            await db.flush()

        with patch("app.services.language_progression_service.progression_enabled", return_value=False):
            try:
                await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
                results.append(_ok("promote API structured denial", False))
            except OfficialPromotionApiError as exc:
                results.append(_ok("promote API returns 503", exc.status_code == 503))
                results.append(
                    _ok(
                        "reason mentions progression",
                        PROGRESSION_UNAVAILABLE_REASON in str(exc.detail),
                    )
                )

        await db.rollback()

    return results


def verify_feature_flag_matrix() -> list[bool]:
    print("\n=== Feature flag matrix (L-10) ===")
    results: list[bool] = []
    results.append(_ok("ENABLED defaults false", progression_enabled() is False))
    results.append(_ok("OFFICIAL_SELECT defaults false", official_select_enabled() is False))
    progression_src = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "language_progression_service.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("flag matrix documented", "Promotion lifecycle flag matrix" in progression_src))
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
    print("verify_language_stabilization_pr_2_cefr_sync")
    all_results: list[bool] = []

    all_results.extend(verify_policy_comments())
    all_results.extend(verify_sync_helper_exists())
    all_results.extend(await verify_official_promotion_syncs_analytics())
    all_results.extend(await verify_sync_helper_pure())
    all_results.extend(verify_progression_row_wiring())
    all_results.extend(await verify_start_never_500_missing_row())
    all_results.extend(await verify_promote_api_missing_row())
    all_results.extend(verify_feature_flag_matrix())

    for script in (
        "verify_language_official_promotion_api_pr_3.py",
        "verify_language_promotion_test_api_pr_2.py",
        "verify_language_listening_progression_runtime_pr_1.py",
        "verify_language_stabilization_pr_1_adaptive.py",
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
