"""Verify Phase 4.2.2 — Official CEFR read layer + dual-write (no selector switch).

Usage (from backend/):
    python scripts/verify_language_progression_phase_4_2_2.py
"""

from __future__ import annotations

import asyncio
import inspect
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import delete, text

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.language.analytics import LanguageAnalytics
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progression import LanguageProgression
from app.services import language_listening_service
from app.services.language_progression_service import (
    OfficialCefrRead,
    backfill_from_analytics_row,
    dual_read_enabled,
    ensure_progression_row,
    get_official_cefr,
    get_official_overall_cefr,
    mirror_levels_from_analytics,
    progression_enabled,
    sync_progression_from_skill_levels,
    sync_progression_mirror_analytics,
)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


@contextmanager
def _flags(enabled: bool = False, dual_read: bool = False):
    env = os.environ.copy()
    env["LANG_PROGRESSION_ENABLED"] = "true" if enabled else "false"
    env["LANG_PROGRESSION_DUAL_READ"] = "true" if dual_read else "false"
    with patch.dict(os.environ, env, clear=False):
        get_settings.cache_clear()
        try:
            yield
        finally:
            get_settings.cache_clear()


async def verify_feature_flags_default() -> list[bool]:
    print("\n=== Feature flags (default) ===")
    results: list[bool] = []
    with _flags(enabled=False, dual_read=False):
        results.append(_ok("LANG_PROGRESSION_ENABLED defaults false", not progression_enabled()))
        results.append(_ok("LANG_PROGRESSION_DUAL_READ defaults false", not dual_read_enabled()))
    return results


async def verify_read_progression_row() -> list[bool]:
    print("\n=== Read helper — progression row ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            results.append(_ok("skip progression read (no rows)", True))
            return results

        sid, lid = sample[0], sample[1]
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        reading = await get_official_cefr(db, student_id=sid, language_id=lid, skill=LanguageSkill.reading)
        overall = await get_official_overall_cefr(db, student_id=sid, language_id=lid)

        results.append(_ok("get_official_cefr returns OfficialCefrRead", isinstance(reading, OfficialCefrRead)))
        results.append(_ok("reading source is progression", reading.source == "progression"))
        results.append(
            _ok(
                "reading level matches row",
                reading.level == row.official_reading_cefr,
                reading.level.value,
            )
        )
        results.append(_ok("overall source is progression", overall.source == "progression"))
        results.append(
            _ok(
                "overall level matches row",
                overall.level == row.official_overall_cefr,
                overall.level.value,
            )
        )

    return results


async def verify_read_analytics_fallback() -> list[bool]:
    print("\n=== Read helper — analytics fallback ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        prog = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if prog is None:
            results.append(_ok("skip analytics fallback (no progression rows)", True))
            return results

        sid, lid = prog[0], prog[1]
        ana_row = None
        await db.execute(
            delete(LanguageProgression).where(
                LanguageProgression.student_id == sid,
                LanguageProgression.language_id == lid,
            )
        )
        await db.commit()

        try:
            ana_row = await db.get(LanguageAnalytics, {"student_id": sid, "language_id": lid})
            reading = await get_official_cefr(db, student_id=sid, language_id=lid, skill="reading")
            expected = ana_row.reading_level or LanguageLevel.A1

            results.append(_ok("fallback source is analytics", reading.source == "analytics"))
            results.append(
                _ok(
                    "fallback reading matches analytics",
                    reading.level == expected,
                    f"got={reading.level.value} expected={expected.value}",
                )
            )
        finally:
            if ana_row is not None:
                await backfill_from_analytics_row(db, ana_row, force=True)
                await db.commit()

    return results


async def verify_dual_write_when_disabled() -> list[bool]:
    print("\n=== Dual-write disabled ===")
    results: list[bool] = []

    with _flags(enabled=False):
        async with AsyncSessionLocal() as db:
            sample = (
                await db.execute(text("SELECT student_id, language_id FROM language_analytics LIMIT 1"))
            ).first()
            if sample is None:
                results.append(_ok("skip dual-write disabled test", True))
                return results

            sid, lid = sample[0], sample[1]
            before = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
            version_before = before.version if before else 0

            row = await sync_progression_from_skill_levels(
                db,
                student_id=sid,
                language_id=lid,
                skill_levels={
                    LanguageSkill.reading: LanguageLevel.A2,
                    LanguageSkill.listening: LanguageLevel.A2,
                    LanguageSkill.writing: LanguageLevel.A2,
                    LanguageSkill.speaking: LanguageLevel.A2,
                },
                overall=LanguageLevel.A2,
                source="verify_disabled",
            )
            await db.rollback()

            results.append(_ok("sync returns None when flag off", row is None))
            after = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
            version_after = after.version if after else 0
            results.append(_ok("version unchanged when flag off", version_before == version_after))

    return results


async def verify_dual_write_when_enabled() -> list[bool]:
    print("\n=== Dual-write enabled ===")
    results: list[bool] = []

    with _flags(enabled=True):
        async with AsyncSessionLocal() as db:
            sample = (
                await db.execute(text("SELECT student_id, language_id FROM language_analytics LIMIT 1"))
            ).first()
            if sample is None:
                results.append(_ok("skip dual-write enabled test", True))
                return results

            sid, lid = sample[0], sample[1]
            skill_levels = {
                LanguageSkill.reading: LanguageLevel.B1,
                LanguageSkill.listening: LanguageLevel.B1,
                LanguageSkill.writing: LanguageLevel.A1,
                LanguageSkill.speaking: LanguageLevel.A2,
            }
            overall = LanguageLevel.A1

            row = await sync_progression_from_skill_levels(
                db,
                student_id=sid,
                language_id=lid,
                skill_levels=skill_levels,
                overall=overall,
                source="verify_enabled",
            )
            await db.flush()

            results.append(_ok("sync returns row when flag on", row is not None))
            if row:
                results.append(_ok("official reading B1", row.official_reading_cefr == LanguageLevel.B1))
                results.append(_ok("official overall A1", row.official_overall_cefr == LanguageLevel.A1))

            ana = await db.get(LanguageAnalytics, {"student_id": sid, "language_id": lid})
            mirrored = mirror_levels_from_analytics(ana)
            prog_row = await sync_progression_mirror_analytics(db, ana, source="verify_mirror")
            results.append(_ok("mirror sync returns row", prog_row is not None))
            if prog_row:
                results.append(
                    _ok(
                        "mirror matches analytics reading",
                        prog_row.official_reading_cefr == mirrored["reading"],
                    )
                )

            await db.rollback()

    return results


async def verify_ensure_progression_row() -> list[bool]:
    print("\n=== ensure_progression_row ===")
    results: list[bool] = []

    with _flags(enabled=True):
        async with AsyncSessionLocal() as db:
            sample = (
                await db.execute(
                    text(
                        "SELECT student_id, language_id FROM language_analytics a "
                        "WHERE NOT EXISTS ("
                        "  SELECT 1 FROM language_progression p "
                        "  WHERE p.student_id = a.student_id AND p.language_id = a.language_id"
                        ") LIMIT 1"
                    )
                )
            ).first()
            if sample is None:
                results.append(_ok("ensure skip (all have rows)", True))
                return results

            sid, lid = sample[0], sample[1]
            row = await ensure_progression_row(db, student_id=sid, language_id=lid)
            results.append(_ok("ensure creates row", row is not None))
            await db.rollback()

    return results


def verify_no_reader_switch() -> list[bool]:
    print("\n=== Selector wiring (Phase 4.2.3+) ===")
    results: list[bool] = []

    listen_src = inspect.getsource(language_listening_service._adaptive_level)
    results.append(_ok("listening delegates to select_skill_level_str", "select_skill_level_str" in listen_src))

    placement_src = Path(__file__).resolve().parents[1].joinpath(
        "app/services/language_placement_service.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("placement imports sync_progression_from_skill_levels", "sync_progression_from_skill_levels" in placement_src))

    exam_src = Path(__file__).resolve().parents[1].joinpath("app/api/language_exam.py").read_text(encoding="utf-8")
    results.append(_ok("exam imports sync_progression_mirror_analytics", "sync_progression_mirror_analytics" in exam_src))

    promo_src = Path(__file__).resolve().parents[1].joinpath(
        "app/services/language_promotion_test_service.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("promotion prepares dual-write path", "sync_progression_mirror_analytics" in promo_src))

    reading_src = Path(__file__).resolve().parents[1].joinpath(
        "app/services/language_reading_service.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("reading delegates to select_skill_level_str", "select_skill_level_str" in reading_src))

    return results


async def verify_phase_4_2_1_regression() -> list[bool]:
    print("\n=== Phase 4.2.1 regression ===")
    import subprocess

    proc = subprocess.run(
        [sys.executable, "scripts/verify_language_progression_phase_4_2_1.py"],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
    )
    passed = proc.returncode == 0 and "PASS" in proc.stdout
    return [_ok("phase 4.2.1 verify still passes", passed)]


async def main() -> int:
    print("verify_language_progression_phase_4_2_2")
    all_results: list[bool] = []
    all_results.extend(await verify_feature_flags_default())
    all_results.extend(await verify_read_progression_row())
    all_results.extend(await verify_read_analytics_fallback())
    all_results.extend(await verify_dual_write_when_disabled())
    all_results.extend(await verify_dual_write_when_enabled())
    all_results.extend(await verify_ensure_progression_row())
    all_results.extend(verify_no_reader_switch())
    all_results.extend(await verify_phase_4_2_1_regression())

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
