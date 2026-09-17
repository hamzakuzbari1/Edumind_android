"""Verify Phase 3.1 — Goal-Aware Learning Engine.

Usage (from backend/):
    python scripts/verify_language_adaptive_learning_phase_3_1.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SIMULATION_RUNS = 500
SIMULATION_LEVEL = "B1"
SIMULATION_GOALS = ("travel", "ielts", "business", "job_interview")
SIMULATION_WEAKNESSES = ["weak inference", "listening detail"]


def audit_static() -> dict[str, object]:
    gen_src = (
        Path(__file__).resolve().parents[1] / "app/services/language_lesson_generation_service.py"
    ).read_text(encoding="utf-8")
    goal_root = Path(__file__).resolve().parents[1] / "app/services/language_learning_goal"

    results: dict[str, object] = {}
    results["generation_wires_goal_engine"] = (
        "recommend_goal_aware_listening_plan" in gen_src
        or "recommend_confidence_aware_listening_plan" in gen_src
        or "recommend_challenge_adaptive_listening_plan" in gen_src
    )
    results["stores_goal_metadata"] = "GOAL_KEY" in gen_src or "listening_learning_goal" in gen_src
    results["goal_prompt_injected"] = "LEARNING GOAL" in gen_src
    results["curriculum_engine_unmodified_call"] = "recommend_curriculum_plan" not in gen_src.replace(
        "recommend_goal_aware_listening_plan", ""
    )
    results["goal_package_exists"] = goal_root.is_dir()
    results["profiles_module_exists"] = (goal_root / "profiles.py").is_file()

    from app.services.language_learning_goal import LearningGoal, all_profiles
    from app.services.language_learning_goal.scoring import DEFAULT_GOAL_INFLUENCE

    results["supported_goals"] = [g.value for g in LearningGoal]
    results["profile_count"] = len(all_profiles())
    results["goal_influence_default"] = DEFAULT_GOAL_INFLUENCE
    results["goal_influence_in_band"] = 0.10 <= DEFAULT_GOAL_INFLUENCE <= 0.20

    return results


def simulate_goal(
    goal: str,
    *,
    runs: int = SIMULATION_RUNS,
    level: str = SIMULATION_LEVEL,
    goal_influence: float | None = None,
) -> dict[str, object]:
    from app.services.language_learning_goal import LearningGoal, recommend_goal_aware_listening_plan
    from app.services.language_learning_goal.scoring import DEFAULT_GOAL_INFLUENCE
    from app.services.language_listening_curriculum.types import CurriculumHistoryEntry

    learning_goal = LearningGoal(goal)
    influence = goal_influence if goal_influence is not None else DEFAULT_GOAL_INFLUENCE

    intelligence_history = []
    curriculum_history: list[CurriculumHistoryEntry] = []
    records = []
    goal_scores = []
    curriculum_scores = []
    blended_scores = []
    goal_contributions: list[dict[str, float]] = []

    for idx in range(runs):
        rec = recommend_goal_aware_listening_plan(
            level,
            intelligence_history,
            curriculum_history,
            learning_goal=learning_goal,
            themes="present perfect / travel",
            topics="programming, football",
            weaknesses=SIMULATION_WEAKNESSES,
            generation_index=idx,
            goal_influence=influence,
        )
        plan = rec.plan
        records.append(
            {
                "situation": plan.situation.value,
                "format": plan.narrative_format.value,
                "category": plan.category.value,
                "objectives": list(rec.objectives),
                "goal_alignment": rec.goal_alignment.total,
                "curriculum_score": rec.score.total,
                "blended_score": rec.blended_score,
                "goal_influence_pct": rec.goal_influence_pct,
            }
        )
        goal_scores.append(rec.goal_alignment.total)
        curriculum_scores.append(rec.score.total)
        blended_scores.append(rec.blended_score)
        goal_contributions.append(rec.goal_alignment.contributions)

        intelligence_history.append(plan.to_history_entry())
        curriculum_history.append(
            CurriculumHistoryEntry(
                situation=plan.situation.value,
                category=plan.category.value,
                narrative_format=plan.narrative_format.value,
                skill_focus=rec.skill_focus,
                objectives=rec.objectives,
                knowledge_node=rec.knowledge_node,
                level=level,
                generation_index=idx,
                lesson_intent=rec.lesson_intent,
            )
        )

    situation_dist = dict(Counter(r["situation"] for r in records).most_common())
    format_dist = dict(Counter(r["format"] for r in records).most_common())
    objective_dist = dict(Counter(oid for r in records for oid in r["objectives"]).most_common(12))

    profile = __import__(
        "app.services.language_learning_goal.profiles",
        fromlist=["profile_for_goal"],
    ).profile_for_goal(learning_goal)
    preferred_hits = sum(1 for r in records if r["situation"] in profile.preferred_situations)
    preferred_rate = round(preferred_hits / runs, 3)

    contrib_avg: dict[str, float] = {}
    if goal_contributions:
        for key in goal_contributions[0]:
            contrib_avg[key] = round(
                sum(c.get(key, 0.0) for c in goal_contributions) / len(goal_contributions),
                4,
            )

    avg_goal = round(sum(goal_scores) / len(goal_scores), 4)
    avg_curriculum = round(sum(curriculum_scores) / len(curriculum_scores), 4)
    avg_blended = round(sum(blended_scores) / len(blended_scores), 4)
    goal_delta = round(avg_blended - avg_curriculum, 4)

    return {
        "goal": goal,
        "runs": runs,
        "level": level,
        "goal_influence_pct": influence,
        "situation_distribution": situation_dist,
        "format_distribution": format_dist,
        "objective_distribution_top12": objective_dist,
        "preferred_situation_rate": preferred_rate,
        "avg_goal_alignment": avg_goal,
        "avg_curriculum_score": avg_curriculum,
        "avg_blended_score": avg_blended,
        "goal_score_delta_vs_curriculum": goal_delta,
        "goal_contributions_avg": contrib_avg,
        "top_situations": list(situation_dist.keys())[:5],
    }


def simulate_baseline_no_goal(*, runs: int = SIMULATION_RUNS, level: str = SIMULATION_LEVEL) -> dict[str, object]:
    """Before: curriculum-only recommendation without goal weighting."""
    from app.services.language_listening_curriculum import recommend_curriculum_plan
    from app.services.language_listening_curriculum.types import CurriculumHistoryEntry

    intelligence_history = []
    curriculum_history: list[CurriculumHistoryEntry] = []
    situations = Counter()

    for idx in range(runs):
        rec = recommend_curriculum_plan(
            level,
            intelligence_history,
            curriculum_history,
            themes="present perfect / travel",
            topics="programming, football",
            weaknesses=SIMULATION_WEAKNESSES,
            generation_index=idx,
        )
        plan = rec.plan
        situations[plan.situation.value] += 1
        intelligence_history.append(plan.to_history_entry())
        curriculum_history.append(
            CurriculumHistoryEntry(
                situation=plan.situation.value,
                category=plan.category.value,
                narrative_format=plan.narrative_format.value,
                skill_focus=rec.skill_focus,
                objectives=rec.objectives,
                knowledge_node=rec.knowledge_node,
                level=level,
                generation_index=idx,
                lesson_intent=rec.lesson_intent,
            )
        )

    return {
        "runs": runs,
        "situation_distribution": dict(situations.most_common()),
        "note": "Curriculum-only baseline (no goal profile weighting)",
    }


def _top_share(dist: dict[str, int], key: str) -> float:
    total = sum(dist.values()) or 1
    return dist.get(key, 0) / total


def main() -> int:
    static = audit_static()
    before = simulate_baseline_no_goal()
    simulations = {goal: simulate_goal(goal) for goal in SIMULATION_GOALS}

    travel = simulations["travel"]
    ielts = simulations["ielts"]
    business = simulations["business"]
    interview = simulations["job_interview"]

    static_checks = [
        ("generation_wires_goal_engine", static.get("generation_wires_goal_engine")),
        ("stores_goal_metadata", static.get("stores_goal_metadata")),
        ("goal_prompt_injected", static.get("goal_prompt_injected")),
        ("goal_package_complete", static.get("goal_package_exists") and static.get("profiles_module_exists")),
        ("ten_supported_goals", (static.get("profile_count") or 0) >= 10),
        ("goal_influence_in_band", static.get("goal_influence_in_band")),
    ]

    sim_checks = [
        ("travel_prefers_travel_situations", travel["preferred_situation_rate"] >= 0.35),
        ("ielts_prefers_academic_situations", ielts["preferred_situation_rate"] >= 0.30),
        ("business_prefers_work_situations", business["preferred_situation_rate"] >= 0.35),
        ("interview_prefers_interview_situations", interview["preferred_situation_rate"] >= 0.25),
        ("goals_diverge_situations", len({tuple(s["top_situations"]) for s in simulations.values()}) >= 2),
        ("goal_influence_nonzero", all(abs(s["goal_score_delta_vs_curriculum"]) >= 0.001 for s in simulations.values())),
        ("goal_alignment_high_for_travel", travel["avg_goal_alignment"] >= 0.55),
        ("goal_alignment_high_for_ielts", ielts["avg_goal_alignment"] >= 0.55),
    ]

    all_checks = static_checks + sim_checks
    overall_pass = all(ok for _, ok in all_checks)

    print("LANGUAGE-ADAPTIVE-LEARNING-PHASE-3.1 VERIFICATION")
    print("=" * 58)
    print("\nSTATIC")
    for key, ok in static_checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print("\nGOAL SIMULATIONS (500 lessons each)")
    for key, ok in sim_checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print(f"\nBEFORE (curriculum-only, n={before['runs']})")
    print(f"  Top situations: {list(before['situation_distribution'].keys())[:6]}")

    for goal, sim in simulations.items():
        print(f"\nAFTER — {goal.upper()} (influence={sim['goal_influence_pct']:.0%})")
        print(f"  Preferred situation rate: {sim['preferred_situation_rate']}")
        print(f"  Avg goal alignment: {sim['avg_goal_alignment']}")
        print(f"  Avg curriculum score: {sim['avg_curriculum_score']}")
        print(f"  Avg blended score: {sim['avg_blended_score']}")
        print(f"  Goal score delta: {sim['goal_score_delta_vs_curriculum']}")
        print("  Situation distribution (top 6):")
        for name, count in list(sim["situation_distribution"].items())[:6]:
            print(f"    {name}: {count}")
        print("  Format distribution:")
        for name, count in list(sim["format_distribution"].items())[:5]:
            print(f"    {name}: {count}")
        print("  Goal contribution averages:")
        for name, val in sorted(sim.get("goal_contributions_avg", {}).items()):
            print(f"    {name}: {val}")

    report = {
        "phase": "3.1",
        "static": static,
        "before": before,
        "simulations": simulations,
        "overall_pass": overall_pass,
    }
    out_path = Path(__file__).resolve().parents[1] / "scripts" / "_phase_3_1_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("-" * 58)
    print(f"  OVERALL: {'PASS' if overall_pass else 'FAIL'}")
    print(f"  Report: {out_path}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
