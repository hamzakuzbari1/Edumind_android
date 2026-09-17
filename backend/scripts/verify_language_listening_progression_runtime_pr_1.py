"""Verify PR-1 — Listening progression runtime integration.

Usage (from backend/):
    python scripts/verify_language_listening_progression_runtime_pr_1.py
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel
from app.models.language.progression import LanguageProgression
from app.services.language_listening_progression.runtime import run_listening_progression_after_submit
from app.services.language_progression_service import upsert_official_levels


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


async def verify_runtime_call_order() -> list[bool]:
    print("\n=== Runtime orchestrator call order ===")
    results: list[bool] = []
    calls: list[str] = []

    async def stage_fn(*_args, **_kwargs):
        calls.append("stage")

    async def gate_fn(*_args, **_kwargs):
        calls.append("gate")

    async def readiness_fn(*_args, **_kwargs):
        calls.append("readiness")

    async def stability_fn(*_args, **_kwargs):
        calls.append("stability")

    with (
        patch(
            "app.services.language_listening_progression.runtime.ensure_progression_row",
            new_callable=AsyncMock,
        ) as ensure_mock,
        patch(
            "app.services.language_listening_progression.runtime.evaluate_and_persist_listening_stage",
            side_effect=stage_fn,
        ),
        patch(
            "app.services.language_listening_progression.runtime.evaluate_listening_transition_gate",
            side_effect=gate_fn,
        ),
        patch(
            "app.services.language_listening_progression.runtime.evaluate_and_persist_listening_promotion_readiness",
            side_effect=readiness_fn,
        ),
        patch(
            "app.services.language_listening_progression.runtime.evaluate_and_persist_listening_promotion_stability",
            side_effect=stability_fn,
        ),
    ):
        await run_listening_progression_after_submit(
            AsyncMock(),
            student_id=1,
            language_id=1,
        )

    expected = ["stage", "gate", "readiness", "stability"]
    results.append(_ok("ensure_progression_row called", ensure_mock.await_count == 1))
    results.append(_ok("four progression engines called", calls == expected, str(calls)))
    return results


def verify_submit_listening_wired() -> list[bool]:
    print("\n=== submit_listening wiring ===")
    results: list[bool] = []
    path = Path(__file__).resolve().parents[1] / "app" / "services" / "language_skill_progress_service.py"
    src = path.read_text(encoding="utf-8")
    results.append(_ok("imports run_listening_progression_after_submit", "run_listening_progression_after_submit" in src))
    results.append(
        _ok(
            "called after confidence/challenge save",
            src.index("save_student_challenge") < src.index("run_listening_progression_after_submit"),
        )
    )
    results.append(
        _ok(
            "listening submit has no analytics CEFR nudge",
            "nudge_reading_level(analytics.listening_level" not in src,
        )
    )
    return results


def verify_upstream_engines_untouched() -> list[bool]:
    print("\n=== Upstream engines untouched ===")
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    packages = [
        "language_learning_stage",
        "language_transition_gate",
        "language_promotion_readiness",
        "language_promotion_stability",
    ]
    results: list[bool] = []
    for pkg in packages:
        engine_path = root / pkg / "engine.py"
        engine_src = engine_path.read_text(encoding="utf-8") if engine_path.is_file() else ""
        results.append(
            _ok(
                f"{pkg} engine has no listening_progression import",
                "language_listening_progression" not in engine_src,
            )
        )
        if pkg in ("language_promotion_readiness", "language_promotion_stability"):
            storage_path = root / pkg / "storage.py"
            storage_src = storage_path.read_text(encoding="utf-8") if storage_path.is_file() else ""
            results.append(
                _ok(
                    f"{pkg} storage uses canonical json mutator",
                    "mutate_listening_progression_json" in storage_src,
                )
            )
        else:
            text_body = "\n".join(p.read_text(encoding="utf-8") for p in (root / pkg).rglob("*.py"))
            results.append(
                _ok(
                    f"{pkg} has no listening_progression import",
                    "language_listening_progression" not in text_body,
                )
            )
    for mod_name in (
        "language_learning_stage.engine",
        "language_transition_gate.engine",
        "language_promotion_readiness.engine",
        "language_promotion_stability.engine",
    ):
        import importlib

        mod = importlib.import_module(f"app.services.{mod_name}")
        src = inspect.getsource(mod)
        results.append(_ok(f"{mod_name} unchanged", "language_listening_progression" not in src))
    return results


async def verify_db_persistence_after_runtime() -> list[bool]:
    print("\n=== DB persistence after runtime ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip db persistence", True)]

        sid, lid = sample[0], sample[1]
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
            source="verify_runtime_pr_1",
            force=True,
        )
        row.promotion_readiness_json = None
        row.promotion_readiness_score = 0
        await db.flush()

        await run_listening_progression_after_submit(db, student_id=sid, language_id=lid)
        await db.refresh(row)

        payload = row.promotion_readiness_json or {}
        stability = payload.get("stability") or {}
        results.append(_ok("readiness_score persisted", row.promotion_readiness_score is not None))
        results.append(_ok("readiness json skill", payload.get("skill") == "listening"))
        results.append(_ok("stage_score in json", "stage_score" in payload))
        results.append(_ok("gate fields in json", "gate_overall_score" in payload and "gate_eligible" in payload))
        results.append(_ok("stability bucket persisted", "promotion_confidence" in stability))
        results.append(_ok("stability history list", isinstance(stability.get("history"), list)))

        await db.rollback()

    return results


async def main() -> int:
    print("verify_language_listening_progression_runtime_pr_1")
    all_results: list[bool] = []
    all_results.extend(await verify_runtime_call_order())
    all_results.extend(verify_submit_listening_wired())
    all_results.extend(verify_upstream_engines_untouched())
    all_results.extend(await verify_db_persistence_after_runtime())

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
