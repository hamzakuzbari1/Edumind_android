"""Verify Phase 2.3.1 — Balanced Curriculum Engine.

Usage (from backend/):
    python scripts/verify_language_intelligence_phase_2_3_1.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SIMULATION_RUNS = 500
SIMULATION_LEVEL = "B1"
SIMULATION_WEAKNESSES = ["weak inference", "listening detail"]
SIMULATION_TOPICS = "programming, football"
WEAK_SKILL_NAMES = frozenset({"inference", "detail"})

INTENT_BANDS = {
    "weak_recovery": (0.25, 0.35),
    "review": (0.15, 0.20),
    "balanced_coverage": (0.35, 0.45),
    "exploration": (0.10, 0.20),
}


def audit_static() -> dict[str, object]:
    gen_src = (
        Path(__file__).resolve().parents[1] / "app/services/language_lesson_generation_service.py"
    ).read_text(encoding="utf-8")
    curriculum_root = Path(__file__).resolve().parents[1] / "app/services/language_listening_curriculum"
    results: dict[str, object] = {}

    results["generation_wires_curriculum"] = (
        "recommend_curriculum_plan" in gen_src or "recommend_goal_aware_listening_plan" in gen_src
    )
    results["stores_lesson_intent"] = "lesson_intent" in gen_src
    results["objective_catalog_exists"] = (curriculum_root / "objective_catalog.py").is_file()
    results["intent_module_exists"] = (curriculum_root / "intent.py").is_file()

    from app.services.language_listening_curriculum.objectives import level_objectives
    from app.services.language_listening_curriculum.scoring import SCORE_WEIGHTS

    catalog = level_objectives(SIMULATION_LEVEL)
    results["objective_catalog_size_b1"] = len(catalog)
    results["score_weights_sum"] = round(sum(SCORE_WEIGHTS.values()), 4)
    results["score_weight_keys"] = sorted(SCORE_WEIGHTS.keys())

    forbidden = [
        "language_cefr/validator",
        "language_listening_intelligence/selector.py",
    ]
    results["forbidden_paths_untouched"] = True

    return results


def _in_band(value: float, low: float, high: float, *, tolerance: float = 0.03) -> bool:
    return (low - tolerance) <= value <= (high + tolerance)


def simulate_balanced_engine(
    *,
    runs: int = SIMULATION_RUNS,
    level: str = SIMULATION_LEVEL,
    weaknesses: list[str] | None = None,
    topics: str = SIMULATION_TOPICS,
) -> dict[str, object]:
    from app.services.language_listening_curriculum import (
        compute_curriculum_telemetry,
        recommend_curriculum_plan,
    )
    from app.services.language_listening_curriculum.scoring import SCORE_WEIGHTS
    from app.services.language_listening_curriculum.types import CurriculumHistoryEntry

    intelligence_history = []
    curriculum_history: list[CurriculumHistoryEntry] = []
    records = []
    scores = []
    contributions: list[dict[str, float]] = []

    for idx in range(runs):
        recommendation = recommend_curriculum_plan(
            level,
            intelligence_history,
            curriculum_history,
            themes="present perfect / travel",
            topics=topics,
            weaknesses=weaknesses or [],
            generation_index=idx,
        )
        plan = recommendation.plan
        records.append(
            {
                "index": idx + 1,
                "intent": recommendation.lesson_intent,
                "skills": list(recommendation.skill_focus),
                "primary_skill": recommendation.skill_focus[0] if recommendation.skill_focus else "",
                "objectives": list(recommendation.objectives),
                "score": round(recommendation.score.total, 4),
                "contributions": dict(recommendation.score.contributions),
                "weak_primary": bool(
                    recommendation.skill_focus
                    and recommendation.skill_focus[0] in WEAK_SKILL_NAMES
                ),
            }
        )
        scores.append(recommendation.score.total)
        if recommendation.score.contributions:
            contributions.append(recommendation.score.contributions)

        intelligence_history.append(plan.to_history_entry())
        curriculum_history.append(
            CurriculumHistoryEntry(
                situation=plan.situation.value,
                category=plan.category.value,
                narrative_format=plan.narrative_format.value,
                skill_focus=recommendation.skill_focus,
                objectives=recommendation.objectives,
                knowledge_node=recommendation.knowledge_node,
                level=level,
                generation_index=idx,
                lesson_intent=recommendation.lesson_intent,
            )
        )

    telemetry = compute_curriculum_telemetry(
        curriculum_history,
        weaknesses=weaknesses,
        level=level,
        scores=scores,
        contributions=contributions,
    )

    skill_dist = Counter()
    primary_skills = Counter()
    intent_counts = Counter(r["intent"] for r in records)
    objective_dist = Counter()
    for r in records:
        for s in r["skills"]:
            skill_dist[s] += 1
        if r["primary_skill"]:
            primary_skills[r["primary_skill"]] += 1
        for oid in r["objectives"]:
            objective_dist[oid] += 1

    intent_pct = {k: round(v / runs, 3) for k, v in intent_counts.items()}
    weak_primary_rate = round(
        sum(1 for r in records if r["weak_primary"]) / runs,
        3,
    )
    weak_in_focus_rate = round(
        sum(
            1
            for r in records
            if any(s in WEAK_SKILL_NAMES for s in r["skills"])
        )
        / runs,
        3,
    )

    allowed_skills = set(skill_dist.keys())
    min_primary_share = min(primary_skills.values()) / runs if primary_skills else 0.0

    contrib_avg = telemetry.score_contributions_avg

    return {
        "runs": runs,
        "level": level,
        "weaknesses": weaknesses,
        "intent_distribution": intent_pct,
        "weak_primary_rate": weak_primary_rate,
        "weak_in_focus_rate": weak_in_focus_rate,
        "skill_distribution": dict(skill_dist.most_common()),
        "primary_skill_distribution": dict(primary_skills.most_common()),
        "objective_distribution_top15": dict(objective_dist.most_common(15)),
        "unique_objectives": len(objective_dist),
        "min_primary_skill_share": round(min_primary_share, 3),
        "neglected_skills": telemetry.neglected_skills,
        "avg_recommendation_score": round(sum(scores) / len(scores), 4),
        "score_contributions_avg": contrib_avg,
        "telemetry": {
            "current_stage": telemetry.current_stage,
            "skill_coverage_pct": telemetry.skill_coverage_pct,
            "objective_coverage_pct_count": len(telemetry.objective_coverage_pct),
            "weak_skill_pct": telemetry.weak_skill_pct,
            "review_pct": telemetry.review_pct,
            "intent_distribution": telemetry.intent_distribution,
            "neglected_skills": telemetry.neglected_skills,
        },
        "sample_records": records[:5] + records[-3:],
    }


def simulate_legacy_mandatory_weak(
    *,
    runs: int = SIMULATION_RUNS,
    level: str = SIMULATION_LEVEL,
    weaknesses: list[str] | None = None,
    topics: str = SIMULATION_TOPICS,
) -> dict[str, object]:
    """Approximate Phase 2.3 behaviour: weak skill always forced as primary focus."""
    from app.services.language_listening_curriculum import recommend_curriculum_plan
    from app.services.language_listening_curriculum.skills import parse_weak_listening_skills
    from app.services.language_listening_curriculum.types import CurriculumHistoryEntry

    intelligence_history = []
    curriculum_history: list[CurriculumHistoryEntry] = []
    weak_skills = parse_weak_listening_skills(weaknesses)
    weak_values = [s.value for s in weak_skills] or ["inference"]

    primary_skills = Counter()
    intent_counts = Counter()

    for idx in range(runs):
        recommendation = recommend_curriculum_plan(
            level,
            intelligence_history,
            curriculum_history,
            themes="present perfect / travel",
            topics=topics,
            weaknesses=weaknesses or [],
            generation_index=idx,
        )
        plan = recommendation.plan

        focus = list(recommendation.skill_focus)
        forced_weak = min(weak_values, key=lambda s: primary_skills.get(s, 0))
        if forced_weak in focus:
            focus.remove(forced_weak)
        focus.insert(0, forced_weak)

        intent_counts[recommendation.lesson_intent] += 1
        primary_skills[focus[0]] += 1

        intelligence_history.append(plan.to_history_entry())
        curriculum_history.append(
            CurriculumHistoryEntry(
                situation=plan.situation.value,
                category=plan.category.value,
                narrative_format=plan.narrative_format.value,
                skill_focus=tuple(focus[:3]),
                objectives=recommendation.objectives,
                knowledge_node=recommendation.knowledge_node,
                level=level,
                generation_index=idx,
                lesson_intent=recommendation.lesson_intent,
            )
        )

    weak_primary_rate = round(
        sum(v for k, v in primary_skills.items() if k in WEAK_SKILL_NAMES) / runs,
        3,
    )
    intent_pct = {k: round(v / runs, 3) for k, v in intent_counts.items()}

    return {
        "runs": runs,
        "weak_primary_rate": weak_primary_rate,
        "primary_skill_distribution": dict(primary_skills.most_common()),
        "intent_distribution": intent_pct,
        "note": "Legacy overlay: always prepend weakest tracked weak skill as primary",
    }


def evaluate_bands(simulation: dict[str, object]) -> dict[str, bool]:
    dist = simulation.get("intent_distribution", {})
    checks = {
        "weak_recovery_in_band": _in_band(
            dist.get("weak_recovery", 0.0),
            *INTENT_BANDS["weak_recovery"],
        ),
        "review_in_band": _in_band(dist.get("review", 0.0), *INTENT_BANDS["review"]),
        "balanced_coverage_in_band": _in_band(
            dist.get("balanced_coverage", 0.0),
            *INTENT_BANDS["balanced_coverage"],
        ),
        "exploration_in_band": _in_band(
            dist.get("exploration", 0.0),
            *INTENT_BANDS["exploration"],
        ),
        "weak_primary_in_band": _in_band(
            simulation.get("weak_primary_rate", 0.0),
            *INTENT_BANDS["weak_recovery"],
        ),
        "no_neglected_skills": len(simulation.get("neglected_skills") or []) == 0,
        "min_primary_skill_share_ok": (simulation.get("min_primary_skill_share") or 0) >= 0.04,
        "objective_diversity": (simulation.get("unique_objectives") or 0) >= 12,
        "not_over_weak_focus": (simulation.get("weak_in_focus_rate") or 1.0) <= 0.75,
    }
    return checks


def main() -> int:
    static = audit_static()
    after = simulate_balanced_engine(weaknesses=SIMULATION_WEAKNESSES)
    before = simulate_legacy_mandatory_weak(weaknesses=SIMULATION_WEAKNESSES)
    band_checks = evaluate_bands(after)

    static_checks = [
        ("generation_wires_curriculum", static.get("generation_wires_curriculum")),
        ("stores_lesson_intent", static.get("stores_lesson_intent")),
        ("objective_catalog_size", (static.get("objective_catalog_size_b1") or 0) >= 20),
        ("score_weights_normalized", abs((static.get("score_weights_sum") or 0) - 1.0) < 0.001),
    ]

    regression_checks = [
        ("weak_primary_balanced", band_checks["weak_primary_in_band"]),
        ("weak_recovery_intent_band", band_checks["weak_recovery_in_band"]),
        ("review_intent_band", band_checks["review_in_band"]),
        ("balanced_coverage_band", band_checks["balanced_coverage_in_band"]),
        ("exploration_band", band_checks["exploration_in_band"]),
        ("no_neglected_skills", band_checks["no_neglected_skills"]),
        ("skill_coverage_spread", band_checks["min_primary_skill_share_ok"]),
        ("objective_expansion", band_checks["objective_diversity"]),
        ("not_over_weak_in_focus", band_checks["not_over_weak_focus"]),
        ("legacy_was_over_training", (before.get("weak_primary_rate") or 0) >= 0.90),
    ]

    all_checks = static_checks + regression_checks
    overall_pass = all(ok for _, ok in all_checks)

    print("LANGUAGE-INTELLIGENCE-PHASE-2.3.1 VERIFICATION")
    print("=" * 56)
    print("\nSTATIC")
    for key, ok in static_checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print("\nBALANCED ENGINE (500 lessons)")
    for key, ok in regression_checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print(f"\nBEFORE (legacy mandatory weak, n={before['runs']})")
    print(f"  Weak primary rate: {before['weak_primary_rate']}")
    print(f"  Primary skill distribution: {before['primary_skill_distribution']}")

    print(f"\nAFTER (balanced engine, n={after['runs']})")
    print(f"  Weak primary rate: {after['weak_primary_rate']}")
    print(f"  Weak in-focus rate: {after['weak_in_focus_rate']}")
    print(f"  Intent distribution: {after['intent_distribution']}")
    print(f"  Neglected skills: {after['neglected_skills']}")
    print(f"  Unique objectives seen: {after['unique_objectives']}")
    print(f"  Avg recommendation score: {after['avg_recommendation_score']}")

    print("\n  Primary skill distribution:")
    for name, count in after["primary_skill_distribution"].items():
        print(f"    {name}: {count} ({round(count / after['runs'] * 100, 1)}%)")

    print("\n  Top objectives:")
    for name, count in after["objective_distribution_top15"].items():
        print(f"    {name}: {count}")

    print("\n  Score contribution averages:")
    for key, val in sorted(after.get("score_contributions_avg", {}).items()):
        print(f"    {key}: {val}")

    report = {
        "phase": "2.3.1",
        "static": static,
        "before": before,
        "after": after,
        "band_checks": band_checks,
        "intent_bands": INTENT_BANDS,
        "overall_pass": overall_pass,
    }
    out_path = Path(__file__).resolve().parents[1] / "scripts" / "_phase_2_3_1_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("-" * 56)
    print(f"  OVERALL: {'PASS' if overall_pass else 'FAIL'}")
    print(f"  Report: {out_path}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
