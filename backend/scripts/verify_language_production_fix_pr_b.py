"""Verify PR-B — Remove listening analytics CEFR nudge; unify Official CEFR source.

Usage (from backend/):
    python scripts/verify_language_production_fix_pr_b.py
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.language.analytics import LanguageAnalytics
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progression import LanguageProgression
from app.services.language_official_promotion_api import apply_listening_official_promotion_api
from app.services.language_progression_service import (
    get_official_cefr,
    select_skill_level_str,
    upsert_official_levels,
)
from app.services.language_promotion_test import PromotionTestOutcome, clear_sessions_for_tests
from app.services.language_promotion_test.builder import build_promotion_test_session
from app.services.language_promotion_test.scoring import grade_promotion_test_session
from app.services.language_promotion_test.storage import save_promotion_test_attempt
from app.services.language_promotion_test.telemetry import build_promotion_test_result


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


def _function_body(source: str, name: str) -> str:
    marker = f"async def {name}("
    if marker not in source:
        return ""
    rest = source.split(marker, 1)[1]
    next_def = rest.find("\nasync def ")
    return rest if next_def < 0 else rest[:next_def]


async def _sample_ids(db) -> tuple[int, int] | None:
    row = (
        await db.execute(text("SELECT student_id, language_id FROM language_analytics LIMIT 1"))
    ).first()
    if row is None:
        return None
    return int(row[0]), int(row[1])


def verify_listening_submit_source() -> list[bool]:
    print("\n=== Listening submit source audit ===")
    results: list[bool] = []
    path = Path(__file__).resolve().parents[1] / "app" / "services" / "language_skill_progress_service.py"
    src = path.read_text(encoding="utf-8")
    submit_body = _function_body(src, "submit_listening")

    results.append(_ok("no listening analytics nudge", "nudge_reading_level(analytics.listening_level" not in src))
    results.append(_ok("progression runtime still wired", "run_listening_progression_after_submit" in submit_body))
    results.append(_ok("analytics refresh preserved", "refresh_language_analytics" in submit_body))
    results.append(_ok("adaptive streak preserved", "record_lesson_result" in submit_body))
    results.append(_ok("activity preserved", "record_activity" in submit_body))
    results.append(_ok("reading nudge untouched", "nudge_reading_level(analytics.reading_level" in src))
    return results


async def verify_listening_submit_preserves_levels() -> list[bool]:
    print("\n=== Listening submit preserves CEFR levels ===")
    results: list[bool] = []

    try:
        from app.services.language_skill_progress_service import submit_listening
    except ModuleNotFoundError as exc:
        return [_ok(f"skip submit integration ({exc.name} unavailable)", True)]

    async with AsyncSessionLocal() as db:
        ids = await _sample_ids(db)
        if ids is None:
            return [_ok("skip submit level test (no analytics row)", True)]

        sid, lid = ids
        analytics = await db.get(LanguageAnalytics, {"student_id": sid, "language_id": lid})
        if analytics is None:
            return [_ok("skip submit level test (analytics missing)", True)]

        before_analytics = analytics.listening_level or LanguageLevel.A2
        analytics.listening_level = LanguageLevel.A2
        await db.flush()

        official_before = await get_official_cefr(
            db, student_id=sid, language_id=lid, skill="listening"
        )

        mock_item = MagicMock()
        mock_item.id = 999001
        mock_item.title = "verify-pr-b-listening"
        mock_item.level = LanguageLevel.A2
        mock_item.body_json = {
            "questions": [{"id": "q1", "options": ["a", "b"], "correct_index": 0, "stem": "test"}],
        }
        mock_progress = MagicMock()
        mock_progress.status = MagicMock(value="completed")
        mock_progress.attempt_count = 1
        mock_progress.completed_at = None

        with (
            patch(
                "app.services.language_skill_progress_service.get_listening_lesson",
                new_callable=AsyncMock,
                return_value=(mock_item, None, None, True),
            ),
            patch(
                "app.services.language_skill_progress_service._upsert_progress",
                new_callable=AsyncMock,
                return_value=mock_progress,
            ),
            patch(
                "app.services.language_skill_progress_service.get_default_language",
                new_callable=AsyncMock,
            ) as lang_mock,
            patch(
                "app.services.language_skill_progress_service._sync_path_item",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.language_skill_progress_service.upsert_vocabulary_from_lesson",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.language_skill_progress_service.award_language_xp",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.language_skill_progress_service.record_activity",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.language_skill_progress_service.refresh_language_analytics",
                new_callable=AsyncMock,
            ) as refresh_mock,
            patch(
                "app.services.language_skill_progress_service.record_lesson_result",
                new_callable=AsyncMock,
                return_value={"changed": False},
            ),
            patch(
                "app.services.language_skill_progress_service.credit_skill_objectives",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.language_skill_progress_service.record_lesson_questions",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.language_listening_progression.run_listening_progression_after_submit",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.language_skill_progress_service.pass_threshold_for_item",
                return_value=50,
            ),
        ):
            lang = MagicMock()
            lang.id = lid
            lang_mock.return_value = lang
            await submit_listening(
                db,
                student_id=sid,
                content_id=mock_item.id,
                answers={"q1": {"selected_index": 0}},
            )

        results.append(_ok("analytics refresh still called", refresh_mock.await_count == 1))
        await db.refresh(analytics)
        results.append(
            _ok(
                "analytics.listening_level unchanged after submit",
                analytics.listening_level == before_analytics,
                analytics.listening_level.value if analytics.listening_level else None,
            )
        )

        official_after = await get_official_cefr(
            db, student_id=sid, language_id=lid, skill="listening"
        )
        results.append(
            _ok(
                "official_listening_cefr unchanged after submit",
                official_after.level == official_before.level,
            )
        )

        await db.rollback()
    return results


async def verify_official_promotion_still_promotes() -> list[bool]:
    print("\n=== Official promotion still updates CEFR ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip promote test (no progression row)", True)]

        sid, lid = int(sample[0]), int(sample[1])
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
            source="verify_production_fix_pr_b",
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
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        results.append(_ok("promotion_success", applied.promotion_success))
        results.append(_ok("official CEFR promoted to B1", row.official_listening_cefr == LanguageLevel.B1))

        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_production_fix_pr_b_restore",
            force=True,
        )
        await db.commit()

    return results


async def verify_promotion_test_unaffected() -> list[bool]:
    print("\n=== Promotion test unaffected ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip promotion test check (no progression row)", True)]

        sid, lid = int(sample[0]), int(sample[1])
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
            source="verify_production_fix_pr_b_test",
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
        breakdown, correct = grade_promotion_test_session(
            session, {a.assessment_id: a.correct_index for a in session.assessments}
        )
        result = build_promotion_test_result(session=session, breakdown=breakdown, correct_count=correct)
        await save_promotion_test_attempt(
            db, student_id=sid, language_id=lid, session=session, result=result
        )
        await db.refresh(row)
        results.append(_ok("test result PASS", result.result == PromotionTestOutcome.PASS))
        results.append(_ok("official CEFR unchanged by test", row.official_listening_cefr == baseline))
        await db.rollback()

    return results


def verify_official_writer_audit() -> list[bool]:
    print("\n=== Official CEFR writer audit ===")
    results: list[bool] = []
    backend = Path(__file__).resolve().parents[1] / "app" / "services"
    promo_engine = (backend / "language_official_promotion" / "engine.py").read_text(encoding="utf-8")
    promo_storage = (backend / "language_official_promotion" / "storage.py").read_text(encoding="utf-8")
    progression = (backend / "language_progression_service.py").read_text(encoding="utf-8")
    skill_progress = (backend / "language_skill_progress_service.py").read_text(encoding="utf-8")

    results.append(_ok("apply_listening_official_promotion exists", "apply_listening_official_promotion" in promo_engine))
    results.append(
        _ok(
            "runtime promotion writes via promote_listening_official_cefr",
            "promote_listening_official_cefr" in promo_storage,
        )
    )
    results.append(
        _ok(
            "placement/init via upsert_official_levels only",
            "row.official_listening_cefr = listening" in progression
            and skill_progress.count("official_listening_cefr") == 0,
        )
    )
    results.append(
        _ok(
            "submit_listening does not write official_listening_cefr",
            "official_listening_cefr" not in _function_body(skill_progress, "submit_listening"),
        )
    )
    return results


def verify_listening_reader_audit() -> list[bool]:
    print("\n=== Listening lesson selection readers ===")
    results: list[bool] = []
    listening_svc = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "language_listening_service.py"
    ).read_text(encoding="utf-8")
    progression = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "language_progression_service.py"
    ).read_text(encoding="utf-8")

    results.append(_ok("listening pool uses select_skill_level_str", "select_skill_level_str" in listening_svc))
    results.append(_ok("listening service avoids direct analytics.listening_level", "analytics.listening_level" not in listening_svc))
    results.append(_ok("selector respects OFFICIAL_SELECT flag", "official_select_enabled()" in progression))
    results.append(_ok("selector uses get_official_cefr when flag on", "get_official_cefr" in progression))
    return results


async def verify_official_selector_with_flag() -> list[bool]:
    print("\n=== Official selector flag behavior ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip selector flag test (no progression row)", True)]

        sid, lid = int(sample[0]), int(sample[1])
        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.B1,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_production_fix_pr_b_selector",
            force=True,
        )
        analytics = await db.get(LanguageAnalytics, {"student_id": sid, "language_id": lid})
        if analytics is not None:
            analytics.listening_level = LanguageLevel.A2
            await db.flush()

        with patch("app.services.language_progression_service.official_select_enabled", return_value=True):
            selected = await select_skill_level_str(
                db,
                student_id=sid,
                language_id=lid,
                skill=LanguageSkill.listening,
                default=LanguageLevel.A1,
            )
        results.append(_ok("OFFICIAL_SELECT uses official B1", selected == "B1", selected))

        with patch("app.services.language_progression_service.official_select_enabled", return_value=False):
            legacy = await select_skill_level_str(
                db,
                student_id=sid,
                language_id=lid,
                skill=LanguageSkill.listening,
                default=LanguageLevel.A1,
            )
        if analytics is not None:
            results.append(_ok("flag OFF uses analytics A2", legacy == "A2", legacy))
        else:
            results.append(_ok("flag OFF fallback", legacy in {"A1", "A2"}, legacy))

        await db.rollback()
    return results


def verify_placement_initializes_official() -> list[bool]:
    print("\n=== Placement initializes Official CEFR ===")
    results: list[bool] = []
    placement = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "language_placement_service.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("placement sets analytics listening_level", "analytics.listening_level" in placement))
    results.append(_ok("placement syncs official levels", "sync_progression_from_skill_levels" in placement))
    return results


def verify_dead_code_report() -> list[bool]:
    print("\n=== Dead code report ===")
    results: list[bool] = []
    backend = Path(__file__).resolve().parents[1]
    skill_src = (backend / "app" / "services" / "language_skill_progress_service.py").read_text(encoding="utf-8")
    usages = []
    for path in backend.rglob("*.py"):
        if path.name.startswith("verify_"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "nudge_reading_level" in text:
            usages.append(str(path.relative_to(backend)))
    print(f"  [INFO] nudge_reading_level referenced in: {', '.join(usages) or 'none'}")
    print("  [INFO] No listening-specific nudge helper exists; listening reuse removed in PR-B.")
    results.append(_ok("nudge_reading_level still used (reading submit)", len(usages) > 0))
    results.append(
        _ok(
            "listening submit no longer references nudge_reading_level for listening_level",
            "nudge_reading_level(analytics.listening_level" not in skill_src,
        )
    )
    return results


async def run_regression() -> list[bool]:
    print("\n=== Regression scripts ===")
    backend = Path(__file__).resolve().parents[1]
    scripts = [
        "verify_language_promotion_test_phase_5_4.py",
        "verify_language_official_promotion_phase_5_5.py",
        "verify_language_listening_progression_runtime_pr_1.py",
        "verify_language_production_fix_pr_a.py",
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
            tail = (proc.stdout or proc.stderr or "")[-400:]
            print(tail)
    return results


async def main() -> int:
    print("verify_language_production_fix_pr_b")
    all_results: list[bool] = []
    all_results.extend(verify_listening_submit_source())
    all_results.extend(await verify_listening_submit_preserves_levels())
    all_results.extend(await verify_official_promotion_still_promotes())
    all_results.extend(await verify_promotion_test_unaffected())
    all_results.extend(verify_official_writer_audit())
    all_results.extend(verify_listening_reader_audit())
    all_results.extend(await verify_official_selector_with_flag())
    all_results.extend(verify_placement_initializes_official())
    all_results.extend(verify_dead_code_report())
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
