"""Verify Phase 7.4 curriculum & daily plan.

Usage (from backend/):
    python scripts/verify_language_curriculum.py
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _static_checks() -> dict[str, bool]:
    api_src = (Path(__file__).resolve().parents[1] / "app" / "api" / "language_student.py").read_text(encoding="utf-8")
    progress_src = (Path(__file__).resolve().parents[1] / "app" / "models" / "language" / "progress.py").read_text(
        encoding="utf-8"
    )
    router_src = (Path(__file__).resolve().parents[2] / "src" / "router" / "index.js").read_text(encoding="utf-8")
    tabs_src = (Path(__file__).resolve().parents[2] / "src" / "components" / "language" / "LanguageModuleTabs.vue").read_text(
        encoding="utf-8"
    )
    hub_src = (
        Path(__file__).resolve().parents[2] / "src" / "views" / "student" / "languages" / "StudentLanguagesHubView.vue"
    ).read_text(encoding="utf-8")
    api_js = (Path(__file__).resolve().parents[2] / "src" / "api" / "language.js").read_text(encoding="utf-8")

    cs_path = Path(__file__).resolve().parents[1] / "app" / "services" / "language_curriculum_service.py"
    dp_path = Path(__file__).resolve().parents[1] / "app" / "services" / "language_daily_plan_service.py"
    cs_src = cs_path.read_text(encoding="utf-8")
    dp_src = dp_path.read_text(encoding="utf-8")

    return {
        "curriculum_model": "LanguageCurriculumProgress" in progress_src,
        "migration_file": (Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0041_language_curriculum_progress.py").exists(),
        "curriculum_service": "build_curriculum_overview" in cs_src and "credit_skill_objectives" in cs_src,
        "daily_plan_service": "build_daily_plan" in dp_src,
        "microlesson_service": (Path(__file__).resolve().parents[1] / "app" / "services" / "language_microlesson_service.py").exists(),
        "cefr_levels_a1_c2": all(f'"{lv}"' in cs_src for lv in ["A1", "A2", "B1", "B2", "C1", "C2"]),
        "arabic_learner_curriculum_prompt": "Arabic-speaking" in cs_src,
        "no_shadowing_in_features": '"shadowing"' not in cs_src.split("FEATURES")[1].split("=")[1].split("\n")[0] if "FEATURES" in cs_src else True,
        "api_curriculum_routes": all(x in api_src for x in ["/curriculum", "/daily-plan", "/curriculum/objective/practiced"]),
        "credit_wired_reading": "credit_skill_objectives" in (
            Path(__file__).resolve().parents[1] / "app" / "services" / "language_skill_progress_service.py"
        ).read_text(encoding="utf-8"),
        "credit_wired_writing": "credit_skill_objectives" in (
            Path(__file__).resolve().parents[1] / "app" / "services" / "language_writing_service.py"
        ).read_text(encoding="utf-8"),
        "vue_curriculum_view": (
            Path(__file__).resolve().parents[2] / "src" / "views" / "student" / "languages" / "StudentLanguageCurriculumView.vue"
        ).exists(),
        "router_curriculum": "student-languages-curriculum" in router_src,
        "tabs_curriculum": "STUDENT_LANGUAGES_CURRICULUM" in tabs_src,
        "hub_daily_plan": "fetchDailyPlan" in hub_src and "STUDENT_LANGUAGES_CURRICULUM" in hub_src,
        "frontend_api": all(x in api_js for x in ["fetchCurriculum", "fetchDailyPlan", "markObjectivePracticed"]),
        "schemas_file": (Path(__file__).resolve().parents[1] / "app" / "schemas" / "language_curriculum.py").exists(),
    }


async def _logic_checks() -> dict[str, bool]:
    cs_path = Path(__file__).resolve().parents[1] / "app" / "services" / "language_curriculum_service.py"
    cs_src = cs_path.read_text(encoding="utf-8")
    return {
        "a1_curated_objectives": '"A1":' in cs_src and "Introduce yourself" in cs_src,
        "six_levels_in_curated": all(f'"{lv}":' in cs_src for lv in ["A1", "A2", "B1", "B2", "C1", "C2"]),
        "practice_to_master_3": "PRACTICE_TO_MASTER = 3" in cs_src,
        "skill_features_mapping": '"speaking"' in cs_src and '"conversation"' in cs_src and "SKILL_FEATURES" in cs_src,
        "daily_plan_arabic": "راجع المفردات" in (
            Path(__file__).resolve().parents[1] / "app" / "services" / "language_daily_plan_service.py"
        ).read_text(encoding="utf-8"),
        "microlesson_syria_prompt": "students in Syria" in (
            Path(__file__).resolve().parents[1] / "app" / "services" / "language_microlesson_service.py"
        ).read_text(encoding="utf-8"),
    }


async def main() -> int:
    print("Phase 7.4 — verify_language_curriculum")
    static = _static_checks()
    logic = await _logic_checks()
    all_checks = {**static, **logic}
    for k, v in all_checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    failed = [k for k, v in all_checks.items() if not v]
    if failed:
        print(f"\nFAILED: {', '.join(failed)}")
        return 1
    print(f"\nAll {len(all_checks)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
