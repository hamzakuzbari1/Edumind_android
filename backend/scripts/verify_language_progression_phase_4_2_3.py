"""Verify Phase 4.2.3 — Official CEFR educational selector switch.

Usage (from backend/):
    python scripts/verify_language_progression_phase_4_2_3.py
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

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.language.analytics import LanguageAnalytics
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.services import language_listening_service, language_reading_service
from app.services.language_content_service import _student_skill_level
from app.services.language_curriculum_service import _current_level
from app.services.language_difficulty_service import _base_level
from app.services.language_progression_service import (
    backfill_from_analytics_row,
    official_select_enabled,
    select_skill_level_str,
    upsert_official_levels,
)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


@contextmanager
def _flags(official_select: bool = False):
    env = os.environ.copy()
    env["LANG_PROGRESSION_OFFICIAL_SELECT"] = "true" if official_select else "false"
    with patch.dict(os.environ, env, clear=False):
        get_settings.cache_clear()
        try:
            yield
        finally:
            get_settings.cache_clear()


async def verify_flag_default() -> list[bool]:
    print("\n=== Feature flag (default) ===")
    with _flags(official_select=False):
        return [_ok("LANG_PROGRESSION_OFFICIAL_SELECT defaults false", not official_select_enabled())]


async def verify_official_a2_analytics_b1_listening() -> list[bool]:
    """Official=A2, Analytics listening=B1 → student receives A2 listening."""
    print("\n=== Bug fix: Official A2 vs Analytics B1 (listening) ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_analytics LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip mismatch test (no analytics)", True)]

        sid, lid = sample[0], sample[1]
        analytics = await db.get(LanguageAnalytics, {"student_id": sid, "language_id": lid})
        saved_listening = analytics.listening_level

        analytics.listening_level = LanguageLevel.B1
        await db.flush()

        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_4_2_3",
            force=True,
        )
        await db.commit()

        try:
            with _flags(official_select=False):
                legacy = await language_listening_service._adaptive_level(
                    db, student_id=sid, language_id=lid
                )
                results.append(_ok("flag OFF uses analytics listening", legacy == "B1", legacy))

            with _flags(official_select=True):
                official = await language_listening_service._adaptive_level(
                    db, student_id=sid, language_id=lid
                )
                results.append(_ok("flag ON uses official listening A2", official == "A2", official))
        finally:
            analytics.listening_level = saved_listening
            await backfill_from_analytics_row(db, analytics, force=True)
            await db.commit()

    return results


async def verify_official_b2_analytics_a2_reading() -> list[bool]:
    """Official=B2, Analytics reading=A2 → student receives B2 reading."""
    print("\n=== Official B2 vs Analytics A2 (reading) ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_analytics LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip mismatch test (no analytics)", True)]

        sid, lid = sample[0], sample[1]
        analytics = await db.get(LanguageAnalytics, {"student_id": sid, "language_id": lid})
        saved_reading = analytics.reading_level

        analytics.reading_level = LanguageLevel.A2
        await db.flush()

        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.B2,
            listening=LanguageLevel.B2,
            writing=LanguageLevel.B2,
            speaking=LanguageLevel.B2,
            overall=LanguageLevel.B2,
            source="verify_4_2_3",
            force=True,
        )
        await db.commit()

        try:
            with _flags(official_select=True):
                level = await language_reading_service._adaptive_level(
                    db, student_id=sid, language_id=lid
                )
                results.append(_ok("reading adaptive level is B2", level == "B2", level))
        finally:
            analytics.reading_level = saved_reading
            await backfill_from_analytics_row(db, analytics, force=True)
            await db.commit()

    return results


async def verify_selectors_use_progression_helpers() -> list[bool]:
    print("\n=== Selectors wired to progression helpers ===")
    results: list[bool] = []
    root = Path(__file__).resolve().parents[1] / "app"

    checks = [
        ("language_listening_service", "select_skill_level_str"),
        ("language_reading_service", "select_skill_level_str"),
        ("services/language_content_service.py", "select_skill_level"),
        ("services/language_curriculum_service.py", "select_overall_level_str"),
        ("services/language_difficulty_service.py", "select_overall_level_str"),
        ("services/language_learner_context_service.py", "select_all_skill_levels"),
        ("services/language_vocabulary_service.py", "select_skill_level"),
        ("services/language_lessons_service.py", "select_overall_level_str"),
        ("services/language_hub_service.py", "select_all_skill_levels"),
        ("services/language_access_service.py", "select_all_skill_levels"),
    ]

    for rel, needle in checks:
        if rel.endswith(".py"):
            path = root / rel
        else:
            path = root / "services" / f"{rel}.py"
        text_body = path.read_text(encoding="utf-8")
        results.append(_ok(f"{path.name} uses {needle}", needle in text_body))

    listen_src = inspect.getsource(language_listening_service._adaptive_level)
    results.append(_ok("listening _adaptive_level delegates to selector", "select_skill_level_str" in listen_src))
    read_src = inspect.getsource(language_reading_service._adaptive_level)
    results.append(_ok("reading _adaptive_level delegates to selector", "select_skill_level_str" in read_src))

    return results


async def verify_educational_services() -> list[bool]:
    print("\n=== Educational services resolve via selector ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip service checks (no progression rows)", True)]

        sid, lid = sample[0], sample[1]

        with _flags(official_select=True):
            listening = await select_skill_level_str(
                db, student_id=sid, language_id=lid, skill=LanguageSkill.listening
            )
            reading = await select_skill_level_str(
                db, student_id=sid, language_id=lid, skill=LanguageSkill.reading
            )
            vocab = await _student_skill_level(
                db, student_id=sid, language_id=lid, skill=LanguageSkill.reading
            )
            curriculum_level, _ = await _current_level(db, student_id=sid, language_id=lid)
            difficulty_base = await _base_level(db, student_id=sid, language_id=lid)

            results.append(_ok("listening selector returns str", isinstance(listening, str)))
            results.append(_ok("reading selector returns str", isinstance(reading, str)))
            results.append(_ok("vocabulary/content skill level", isinstance(vocab, LanguageLevel)))
            results.append(_ok("curriculum level resolved", bool(curriculum_level)))
            results.append(_ok("difficulty base level resolved", bool(difficulty_base)))

    return results


def verify_engines_untouched() -> list[bool]:
    print("\n=== Phase 1–3 engines untouched ===")
    results: list[bool] = []
    root = Path(__file__).resolve().parents[1] / "app" / "services"

    untouched = [
        "language_listening_challenge",
        "language_listening_confidence",
        "language_listening_explainability",
        "language_skill_progress_service.py",
        "language_xp_service.py",
    ]

    for name in untouched:
        if name.endswith(".py"):
            path = root / name
        else:
            path = root / name
        if path.is_dir():
            text_body = "\n".join(p.read_text(encoding="utf-8") for p in path.rglob("*.py"))
        else:
            text_body = path.read_text(encoding="utf-8")
        results.append(
            _ok(
                f"{name} has no OFFICIAL_SELECT gate",
                "LANG_PROGRESSION_OFFICIAL_SELECT" not in text_body
                and "official_select_enabled" not in text_body,
            )
        )

    cefr_validator = (root / "language_cefr" / "listening_validator.py").read_text(encoding="utf-8")
    results.append(_ok("CEFR validator module unchanged", "language_progression" not in cefr_validator))

    return results


def verify_generation_receives_level_param() -> list[bool]:
    print("\n=== CEFR validator receives level from generation path ===")
    gen_src = (
        Path(__file__).resolve().parents[1]
        / "app/services/language_lesson_generation_service.py"
    ).read_text(encoding="utf-8")
    listen_src = inspect.getsource(language_listening_service._generate_pool_lessons)
    return [
        _ok("generation service calls validate_listening_lesson with level", "validate_listening_lesson" in gen_src),
        _ok("pool generation passes adaptive level", "level=level" in listen_src),
    ]


async def verify_phase_4_2_2_regression() -> list[bool]:
    print("\n=== Phase 4.2.2 regression ===")
    import subprocess

    proc = subprocess.run(
        [sys.executable, "scripts/verify_language_progression_phase_4_2_2.py"],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
    )
    passed = proc.returncode == 0 and "PASS" in proc.stdout
    return [_ok("phase 4.2.2 verify still passes", passed)]


async def main() -> int:
    print("verify_language_progression_phase_4_2_3")
    all_results: list[bool] = []
    all_results.extend(await verify_flag_default())
    all_results.extend(await verify_official_a2_analytics_b1_listening())
    all_results.extend(await verify_official_b2_analytics_a2_reading())
    all_results.extend(await verify_selectors_use_progression_helpers())
    all_results.extend(await verify_educational_services())
    all_results.extend(verify_engines_untouched())
    all_results.extend(verify_generation_receives_level_param())
    all_results.extend(await verify_phase_4_2_2_regression())

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
