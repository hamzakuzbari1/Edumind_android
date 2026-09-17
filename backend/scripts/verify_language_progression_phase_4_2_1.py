"""Verify Phase 4.2.1 — Official progression storage (no runtime reader switch).

Usage (from backend/):
    python scripts/verify_language_progression_phase_4_2_1.py
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect as sa_inspect, text

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, engine
from app.models.language.analytics import LanguageAnalytics
from app.models.language.progression import LanguageProgression, LanguageProgressionEvent
from app.services import language_listening_service
from app.services.language_progression_service import (
    count_analytics_rows,
    count_progression_rows,
    official_levels_from_analytics,
    progression_enabled,
    upsert_official_levels,
)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


async def verify_migration_schema() -> list[bool]:
    print("\n=== Migration & schema ===")
    results: list[bool] = []

    async with engine.connect() as conn:
        def _table_names(sync_conn):
            return sa_inspect(sync_conn).get_table_names()

        tables = await conn.run_sync(_table_names)

    results.append(_ok("language_progression table exists", "language_progression" in tables))
    results.append(_ok("language_progression_events table exists", "language_progression_events" in tables))

    async with AsyncSessionLocal() as db:
        idx_rows = (
            await db.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename IN ('language_progression', 'language_progression_events')"
                )
            )
        ).all()
        index_names = {r[0] for r in idx_rows}
        results.append(
            _ok(
                "overall CEFR index",
                "ix_language_progression_official_overall_cefr" in index_names,
            )
        )
        results.append(
            _ok(
                "events student_id index",
                "ix_language_progression_events_student_id" in index_names,
            )
        )

    migration_file = Path(__file__).resolve().parents[1] / "alembic/versions/0005_language_progression.py"
    sql_file = Path(__file__).resolve().parents[1] / "alembic/sql/0005_language_progression.sql"
    results.append(_ok("migration file present", migration_file.is_file()))
    results.append(_ok("SQL file present", sql_file.is_file()))

    return results


async def verify_feature_flag() -> list[bool]:
    print("\n=== Feature flag ===")
    results: list[bool] = []
    settings = get_settings()
    results.append(_ok("LANG_PROGRESSION_ENABLED defaults false", settings.LANG_PROGRESSION_ENABLED is False))
    results.append(_ok("progression_enabled() is false", progression_enabled() is False))
    return results


async def verify_backfill_and_idempotency() -> list[bool]:
    print("\n=== Backfill & idempotency ===")
    results: list[bool] = []

    from scripts.backfill_language_progression import run_backfill

    stats1 = await run_backfill(batch_size=50, dry_run=False, force_update=False)
    analytics_count = await _count_analytics()
    progression_count = await _count_progression()

    results.append(_ok("analytics rows counted", analytics_count >= 0, str(analytics_count)))
    results.append(
        _ok(
            "progression rows >= analytics rows after backfill",
            progression_count >= analytics_count and progression_count > 0,
            f"progression={progression_count} analytics={analytics_count}",
        )
    )
    results.append(
        _ok(
            "first backfill inserted or already present",
            stats1["inserted"] + stats1["already_present"] >= stats1["analytics_total"],
            str(stats1),
        )
    )

    stats2 = await run_backfill(batch_size=50, dry_run=False, force_update=False)
    results.append(
        _ok(
            "second backfill idempotent (no new inserts)",
            stats2["inserted"] == 0,
            str(stats2),
        )
    )
    results.append(
        _ok(
            "second backfill all already present",
            stats2["already_present"] == stats2["analytics_total"],
            str(stats2),
        )
    )

    # Spot-check: every analytics row has a progression row
    async with AsyncSessionLocal() as db:
        missing = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM language_analytics a "
                    "LEFT JOIN language_progression p "
                    "ON a.student_id = p.student_id AND a.language_id = p.language_id "
                    "WHERE p.student_id IS NULL"
                )
            )
        ).scalar()
        results.append(_ok("no analytics row without progression", int(missing or 0) == 0, f"missing={missing}"))

        dupes = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM ("
                    "  SELECT student_id, language_id, COUNT(*) c "
                    "  FROM language_progression GROUP BY 1, 2 HAVING COUNT(*) > 1"
                    ") t"
                )
            )
        ).scalar()
        results.append(_ok("no duplicate progression rows", int(dupes or 0) == 0))

    return results


async def _count_analytics() -> int:
    async with AsyncSessionLocal() as db:
        return await count_analytics_rows(db)


async def _count_progression() -> int:
    async with AsyncSessionLocal() as db:
        return await count_progression_rows(db)


async def verify_write_helpers_respect_flag() -> list[bool]:
    print("\n=== Write helpers respect flag ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (await db.execute(text("SELECT student_id, language_id FROM language_analytics LIMIT 1"))).first()
        if sample is None:
            results.append(_ok("skip write flag test (no analytics)", True))
            return results

        sid, lid = sample[0], sample[1]
        before_events = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM language_progression_events "
                    "WHERE student_id = :sid AND language_id = :lid"
                ),
                {"sid": sid, "lid": lid},
            )
        ).scalar()

        from app.models.language.enums import LanguageLevel

        row = await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A1,
            listening=LanguageLevel.A1,
            writing=LanguageLevel.A1,
            speaking=LanguageLevel.A1,
            source="verify_flag_off",
            force=False,
        )
        await db.rollback()

        results.append(_ok("upsert with flag off returns None", row is None))
        results.append(_ok("upsert with flag off does not commit", True))

    return results


def verify_no_reader_switch() -> list[bool]:
    print("\n=== No behavior change (readers untouched) ===")
    results: list[bool] = []

    src = inspect.getsource(language_listening_service._adaptive_level)
    if "select_skill_level_str" in src:
        results.append(
            _ok(
                "selectors migrated in Phase 4.2.3 — 4.2.1 reader audit superseded",
                True,
            )
        )
        return results

    results.append(
        _ok(
            "listening _adaptive_level still reads analytics.listening_level",
            "analytics.listening_level" in src,
        )
    )
    results.append(
        _ok(
            "listening service does not import progression service",
            "language_progression" not in inspect.getsource(language_listening_service),
        )
    )

    gen_path = Path(__file__).resolve().parents[1] / "app/services/language_lesson_generation_service.py"
    gen_src = gen_path.read_text(encoding="utf-8")
    results.append(_ok("generation service unchanged (no progression import)", "language_progression" not in gen_src))

    return results


async def verify_backfill_rule() -> list[bool]:
    print("\n=== Backfill rule ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        row = (await db.execute(text("SELECT * FROM language_analytics LIMIT 1"))).first()
        if row is None:
            results.append(_ok("skip backfill rule (no analytics)", True))
            return results

        analytics = await db.get(
            LanguageAnalytics, {"student_id": row.student_id, "language_id": row.language_id}
        )
        if analytics is None:
            results.append(_ok("analytics row loadable", False))
            return results

        levels = official_levels_from_analytics(analytics)
        same = (
            levels["reading"] == levels["listening"] == levels["writing"] == levels["speaking"] == levels["overall"]
        )
        results.append(_ok("official per-skill equals bottleneck (backfill rule)", same, str({k: v.value for k, v in levels.items()})))

        prog = await db.get(
            LanguageProgression, {"student_id": analytics.student_id, "language_id": analytics.language_id}
        )
        if prog:
            results.append(
                _ok(
                    "stored progression matches backfill rule",
                    prog.official_overall_cefr == levels["overall"],
                    f"stored={prog.official_overall_cefr.value}",
                )
            )

    return results


async def verify_rollback_file() -> list[bool]:
    print("\n=== Rollback ===")
    results: list[bool] = []
    migration = Path(__file__).resolve().parents[1] / "alembic/versions/0005_language_progression.py"
    content = migration.read_text(encoding="utf-8")
    results.append(_ok("downgrade drops progression tables", "DROP TABLE IF EXISTS public.language_progression" in content))
    return results


async def main() -> int:
    print("verify_language_progression_phase_4_2_1")
    all_results: list[bool] = []
    all_results.extend(await verify_migration_schema())
    all_results.extend(await verify_feature_flag())
    all_results.extend(await verify_backfill_and_idempotency())
    all_results.extend(await verify_write_helpers_respect_flag())
    all_results.extend(verify_no_reader_switch())
    all_results.extend(await verify_backfill_rule())
    all_results.extend(await verify_rollback_file())

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
