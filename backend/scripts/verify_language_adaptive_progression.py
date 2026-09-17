"""Verify Phase 7.5 core adaptive progression.

Usage (from backend/):
    python scripts/verify_language_adaptive_progression.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]


def _static_checks() -> dict[str, bool]:
    api = (BACKEND / "app" / "api" / "language_student.py").read_text(encoding="utf-8")
    adaptive = (BACKEND / "app" / "services" / "language_adaptive_service.py").read_text(encoding="utf-8")
    daily = (BACKEND / "app" / "services" / "language_daily_plan_service.py").read_text(encoding="utf-8")
    schema = (BACKEND / "app" / "schemas" / "language_adaptive.py").read_text(encoding="utf-8")
    cur = (BACKEND / "app" / "schemas" / "language_curriculum.py").read_text(encoding="utf-8")
    return {
        "adaptive_state_route": '"/adaptive/state"' in api and "AdaptiveStateOut" in api,
        "build_adaptive_state": "async def build_adaptive_state" in adaptive,
        "compute_skill_recommendation": "def compute_skill_recommendation" in adaptive,
        "promote_maintain_remedial": all(x in adaptive for x in ["PROMOTE", "MAINTAIN", "REMEDIAL"]),
        "sort_objectives": "def sort_objectives_for_adaptive" in adaptive,
        "daily_plan_uses_adaptive": "build_adaptive_state" in daily and "sort_objectives_for_adaptive" in daily,
        "daily_plan_recommendation_field": "adaptive_recommendation" in cur,
        "schema_strengths_weaknesses": "strengths" in schema and "weaknesses" in schema,
        "no_level_jump": '"changed": False' in adaptive,
    }


def _persona_cases() -> dict[str, bool]:
    from app.services.language_adaptive_service import (
        compute_overall_recommendation,
        compute_skill_recommendation,
        derive_strengths_weaknesses,
        rolling_average,
        sort_objectives_for_adaptive,
    )

    window, up, down = 8, 82.0, 40.0

    strong_scores = {
        "reading": [90, 88, 92, 85, 91],
        "listening": [87, 90, 86, 88, 89],
        "writing": [84, 86, 88, 85, 87],
        "speaking": [83, 85, 86, 84, 88],
    }
    weak_scores = {
        "reading": [38, 42, 35, 40],
        "listening": [45, 38, 42],
        "writing": [50, 48, 52],
        "speaking": [35, 38, 36, 40],
    }
    average_scores = {
        "reading": [68, 72, 70, 65],
        "listening": [70, 68, 71],
        "writing": [66, 69, 67],
        "speaking": [64, 68, 70],
    }

    def _snapshots(score_map: dict[str, list[float]]) -> dict[str, dict]:
        out = {}
        for skill, scores in score_map.items():
            avg = rolling_average(scores)
            rec = compute_skill_recommendation(scores, avg, window_size=window, up_threshold=up, down_threshold=down)
            out[skill] = {
                "rolling_average": avg,
                "recommendation": rec,
                "samples_in_window": len(scores),
                "recent_scores": scores,
            }
        return out

    strong = _snapshots(strong_scores)
    weak = _snapshots(weak_scores)
    average = _snapshots(average_scores)

    strong_rec = compute_overall_recommendation(
        strong, window_size=window, up_threshold=up, down_threshold=down
    )
    weak_rec = compute_overall_recommendation(
        weak, window_size=window, up_threshold=up, down_threshold=down
    )
    average_rec = compute_overall_recommendation(
        average, window_size=window, up_threshold=up, down_threshold=down
    )

    strong_strengths, strong_weak = derive_strengths_weaknesses(
        strong, up_threshold=up, down_threshold=down
    )
    weak_strengths, weak_weak = derive_strengths_weaknesses(
        weak, up_threshold=up, down_threshold=down
    )

    objectives = [
        {"id": "B1-1", "title": "Basics", "feature": "reading", "status": "in_progress", "grammar": "present"},
        {"id": "B1-2", "title": "Opinions", "feature": "writing", "status": "new", "grammar": "because"},
        {"id": "B1-3", "title": "Debate", "feature": "conversation", "status": "new", "grammar": "clauses"},
    ]
    promote_order = sort_objectives_for_adaptive(
        objectives, recommendation="PROMOTE", strengths=["writing"], weaknesses=[]
    )
    remedial_order = sort_objectives_for_adaptive(
        objectives, recommendation="REMEDIAL", strengths=[], weaknesses=["reading"]
    )

    print("\nAdaptive persona examples")
    print("-------------------------")
    for label, rec, snaps, strengths, weaknesses in (
        ("Strong student", strong_rec, strong, strong_strengths, strong_weak),
        ("Average student", average_rec, average, [], []),
        ("Weak student", weak_rec, weak, weak_strengths, weak_weak),
    ):
        avgs = {k: v["rolling_average"] for k, v in snaps.items()}
        print(f"  {label}:")
        print(f"    recommendation: {rec}")
        print(f"    rolling_averages: {json.dumps(avgs)}")
        print(f"    strengths: {strengths}")
        print(f"    weaknesses: {weaknesses}")

    return {
        "strong_student_promote": strong_rec == "PROMOTE",
        "weak_student_remedial": weak_rec == "REMEDIAL",
        "average_student_maintain": average_rec == "MAINTAIN",
        "strong_has_strengths": len(strong_strengths) >= 2,
        "weak_has_weaknesses": len(weak_weak) >= 2,
        "promote_sort_prefers_strength": promote_order[0]["feature"] in ("writing", "conversation"),
        "remedial_sort_prefers_weakness": remedial_order[0]["feature"] == "reading",
    }


async def _daily_plan_mock() -> dict[str, bool]:
    from app.services.language_daily_plan_service import build_daily_plan

    overview = {
        "current_level": "B1",
        "mastery_progress_percent": 40,
        "objectives_mastered": 2,
        "objectives_total": 5,
        "objectives": [
            {"id": "B1-1", "title": "A", "feature": "reading", "status": "in_progress", "grammar": "g1"},
            {"id": "B1-5", "title": "E", "feature": "writing", "status": "new", "grammar": "g5"},
        ],
    }
    adaptive_promote = {
        "recommendation": "PROMOTE",
        "strengths": ["writing"],
        "weaknesses": ["speaking"],
    }

    db = AsyncMock()
    with patch(
        "app.services.language_daily_plan_service.build_curriculum_overview",
        new_callable=AsyncMock,
        return_value=overview,
    ), patch(
        "app.services.language_daily_plan_service.build_adaptive_state",
        new_callable=AsyncMock,
        return_value=adaptive_promote,
    ), patch(
        "app.services.language_daily_plan_service.get_default_language",
        new_callable=AsyncMock,
    ) as mock_lang, patch(
        "app.services.language_daily_plan_service._today_events",
        new_callable=AsyncMock,
        return_value=set(),
    ):
        mock_lang.return_value = MagicMock(id=1)
        db.get = AsyncMock(return_value=None)
        plan = await build_daily_plan(db, student_id=1)

    return {
        "daily_plan_has_adaptive_recommendation": plan.get("adaptive_recommendation") == "PROMOTE",
        "daily_plan_challenge_kind": any(it.get("kind") == "objective_challenge" for it in plan.get("items", [])),
    }


def main() -> int:
    print("Phase 7.5 — verify_language_adaptive_progression\n")

    static = _static_checks()
    print("Static checks")
    print("-------------")
    for k, v in static.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    personas = _persona_cases()
    print("\nPersona decision checks")
    print("-----------------------")
    for k, v in personas.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    daily = asyncio.run(_daily_plan_mock())
    print("\nDaily plan integration")
    print("----------------------")
    for k, v in daily.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    all_checks = {**static, **personas, **daily}
    passed = sum(all_checks.values())
    total = len(all_checks)
    print(f"\n{passed}/{total} checks passed.")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
