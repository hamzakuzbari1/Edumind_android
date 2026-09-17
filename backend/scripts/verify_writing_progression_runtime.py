"""Verify Writing progression runtime — mirrors Listening PR-1 checks.

Usage (from backend/):
    python scripts/verify_writing_progression_runtime.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


async def verify_runtime_call_order() -> list[bool]:
    print("\n=== Writing runtime orchestrator call order ===")
    from app.services.language_writing_progression.runtime import run_writing_progression_engines

    results: list[bool] = []
    calls: list[str] = []

    async def stage_fn(*_args, **_kwargs):
        calls.append("stage")

    async def readiness_fn(*_args, **_kwargs):
        calls.append("readiness")

    async def stability_fn(*_args, **_kwargs):
        calls.append("stability")

    with (
        patch(
            "app.services.language_writing_progression.runtime.ensure_progression_row",
            new_callable=AsyncMock,
        ) as ensure_mock,
        patch(
            "app.services.language_writing_progression.runtime.evaluate_and_persist_writing_stage",
            side_effect=stage_fn,
        ),
        patch(
            "app.services.language_writing_progression.runtime.evaluate_and_persist_writing_promotion_readiness",
            side_effect=readiness_fn,
        ),
        patch(
            "app.services.language_writing_progression.runtime.evaluate_and_persist_writing_promotion_stability",
            side_effect=stability_fn,
        ),
    ):
        await run_writing_progression_engines(AsyncMock(), student_id=1, language_id=1)

    expected = ["stage", "readiness", "stability"]
    results.append(_ok("ensure_progression_row called", ensure_mock.await_count == 1))
    results.append(_ok("three progression engines called", calls == expected, str(calls)))
    return results


def verify_packages_exist() -> list[bool]:
    print("\n=== Writing progression packages ===")
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    packages = [
        "language_writing_learning_stage",
        "language_writing_transition_gate",
        "language_writing_promotion_readiness",
        "language_writing_promotion_stability",
        "language_writing_promotion_test",
        "language_writing_official_promotion",
        "language_writing_promotion_test_api",
        "language_writing_official_promotion_api",
    ]
    return [_ok(f"{pkg} exists", (root / pkg).is_dir()) for pkg in packages]


def verify_stage_not_lesson_count_driven() -> list[bool]:
    print("\n=== Stage transitions not lesson-count driven ===")
    engine = Path(__file__).resolve().parents[1] / "app" / "services" / "language_writing_progression" / "engine.py"
    src = engine.read_text(encoding="utf-8")
    results: list[bool] = []
    results.append(_ok("no _stage_from_lessons helper", "_stage_from_lessons" not in src))
    results.append(_ok("mutator keeps current_stage", '"learning_stage": current_stage' in src))
    results.append(_ok("calls run_writing_progression_engines", "run_writing_progression_engines" in src))
    gate = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "language_writing_learning_stage"
        / "engine.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("stage persist gated by transition gate", "eligible_for_next_stage" in gate))
    return results


def verify_api_routes() -> list[bool]:
    print("\n=== API routes registered ===")
    router = Path(__file__).resolve().parents[1] / "app" / "api" / "router.py"
    src = router.read_text(encoding="utf-8")
    results: list[bool] = []
    results.append(_ok("writing promotion test router", "language_writing_promotion_test.router" in src))
    results.append(_ok("writing official promotion router", "language_writing_official_promotion.router" in src))
    promo_api = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "language_writing_promotion_test.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("WPA status route", '"/status"' in promo_api))
    results.append(_ok("WPA start route", '"/start"' in promo_api))
    results.append(_ok("WPA submit route", '"/submit"' in promo_api))
    official = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "language_writing_official_promotion.py"
    ).read_text(encoding="utf-8")
    results.append(_ok("writing promote route", '"/promote"' in official))
    return results


def verify_journey_schema_fields() -> list[bool]:
    print("\n=== Journey bundle exposes progression fields ===")
    schema = (
        Path(__file__).resolve().parents[1] / "app" / "schemas" / "language_writing_bundles.py"
    ).read_text(encoding="utf-8")
    fields = [
        "learning_stage",
        "readiness_score",
        "can_start_wpa",
        "primary_blockers",
        "estimated_lessons_remaining",
        "promotion_target",
    ]
    return [_ok(f"schema field {f}", f"{f}:" in schema) for f in fields]


def verify_frontend_wired() -> list[bool]:
    print("\n=== Frontend promotion wiring ===")
    root = Path(__file__).resolve().parents[2] / "src"
    view = (root / "views/student/languages/StudentLanguageWritingView.vue").read_text(encoding="utf-8")
    api = (root / "api/language.js").read_text(encoding="utf-8")
    results: list[bool] = []
    results.append(_ok("promotion tab in view", 'value="promotion"' in view))
    results.append(_ok("WritingPromotionPanel imported", "WritingPromotionPanel" in view))
    results.append(_ok("useWritingPromotion composable", "useWritingPromotion" in view))
    results.append(_ok("fetchWritingPromotionStatus API", "fetchWritingPromotionStatus" in api))
    results.append(_ok("applyWritingOfficialPromotion API", "applyWritingOfficialPromotion" in api))
    hero = (root / "components/language/WritingJourneyHero.vue").read_text(encoding="utf-8")
    results.append(_ok("hero shows readiness", "readinessScore" in hero))
    results.append(_ok("hero shows blockers", "primaryBlockers" in hero))
    return results


def verify_official_promotion_resets_stage() -> list[bool]:
    print("\n=== Official promotion resets learning stage ===")
    engine = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "services"
        / "language_writing_official_promotion"
        / "engine.py"
    ).read_text(encoding="utf-8")
    results: list[bool] = []
    results.append(_ok("updates official_writing_cefr", "row.official_writing_cefr = new_level" in engine))
    results.append(_ok("resets learning_stage_writing", "row.learning_stage_writing = 1" in engine))
    results.append(_ok("resets writing progression state", 'writing["learning_stage"] = 1' in engine))
    results.append(_ok("clears active WPA session", 'tests["active_session"] = None' in engine))
    return results


async def main() -> int:
    print("Writing Progression Runtime Verification\n")
    results: list[bool] = []
    results.extend(verify_packages_exist())
    results.extend(verify_stage_not_lesson_count_driven())
    results.extend(verify_api_routes())
    results.extend(verify_journey_schema_fields())
    results.extend(verify_frontend_wired())
    results.extend(verify_official_promotion_resets_stage())
    results.extend(await verify_runtime_call_order())

    passed = sum(results)
    total = len(results)
    print(f"\nSummary: {passed}/{total} checks passed")
    if passed == total:
        print("WRITING PROGRESSION RUNTIME VERIFIED")
        return 0
    print("WRITING PROGRESSION NOT READY — fix failures above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
