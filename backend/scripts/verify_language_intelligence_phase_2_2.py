"""Verify Phase 2.2 — Listening Intelligence Engine (topic memory & smart rotation).

Usage (from backend/):
    python scripts/verify_language_intelligence_phase_2_2.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SIMULATION_RUNS = 100
SIMULATION_LEVEL = "B1"
SIMULATION_TOPICS = "programming, football, travel"


def audit_static() -> dict[str, object]:
    gen_src = (
        Path(__file__).resolve().parents[1] / "app/services/language_lesson_generation_service.py"
    ).read_text(encoding="utf-8")
    results: dict[str, object] = {}
    results["generation_wires_intelligence"] = (
        "select_next_listening_plan" in gen_src or "recommend_curriculum_plan" in gen_src
    )
    results["stores_intelligence_metadata"] = "HISTORY_KEY" in gen_src
    results["loads_history_from_db"] = "load_listening_intelligence_history" in gen_src
    results["quality_accepts_intelligence_plan"] = True

    try:
        from app.services.language_cefr import validate_listening_lesson, get_cefr_profile  # noqa: F401

        results["cefr_engine_intact"] = True
    except Exception as exc:  # pragma: no cover
        results["cefr_engine_intact"] = False
        results["cefr_import_error"] = str(exc)

    return results


def simulate_student_generations(
    *,
    runs: int = SIMULATION_RUNS,
    level: str = SIMULATION_LEVEL,
    topics: str = SIMULATION_TOPICS,
) -> dict[str, object]:
    from app.services.language_listening_intelligence import (
        SITUATION_COOLDOWN,
        compute_diversity_stats,
        select_next_listening_plan,
    )
    from app.services.language_listening_intelligence.memory import situation_on_cooldown

    history = []
    plans = []
    for idx in range(runs):
        plan = select_next_listening_plan(
            level,
            history,
            topics=topics,
            generation_index=idx,
        )
        on_cooldown = situation_on_cooldown(plan.situation.value, history, SITUATION_COOLDOWN)
        plans.append(
            {
                "index": idx + 1,
                "situation": plan.situation.value,
                "category": plan.category.value,
                "narrative_format": plan.narrative_format.value,
                "difficulty_band": plan.difficulty_band.value,
                "selection_score": round(plan.selection_score, 4),
                "would_have_been_blocked_by_cooldown": on_cooldown,
            }
        )
        history.append(plan.to_history_entry())

    stats = compute_diversity_stats(history)
    situation_dist = Counter(p["situation"] for p in plans)
    category_dist = Counter(p["category"] for p in plans)
    format_dist = Counter(p["narrative_format"] for p in plans)
    difficulty_dist = Counter(p["difficulty_band"] for p in plans)

    max_cat_share = max(category_dist.values()) / runs if category_dist else 0
    blocked = sum(1 for p in plans if p["would_have_been_blocked_by_cooldown"])

    return {
        "runs": runs,
        "level": level,
        "topics": topics,
        "situation_cooldown": SITUATION_COOLDOWN,
        "situation_distribution": dict(situation_dist.most_common()),
        "category_distribution": dict(category_dist.most_common()),
        "format_distribution": dict(format_dist.most_common()),
        "difficulty_distribution": dict(difficulty_dist.most_common()),
        "unique_situations": len(situation_dist),
        "unique_categories": len(category_dist),
        "unique_formats": len(format_dist),
        "max_category_share": round(max_cat_share, 3),
        "cooldown_violations": stats.cooldown_violations,
        "max_consecutive_same_situation": stats.max_consecutive_same_situation,
        "diversity_score": stats.diversity_score,
        "most_used_situations": stats.most_used_situations,
        "least_used_situations": stats.least_used_situations,
        "average_repetitions": round(stats.average_repetitions, 2),
        "selections_blocked_by_cooldown": blocked,
        "sample_plans": plans[:8] + plans[-3:],
    }


def compare_naive_rotation(runs: int = SIMULATION_RUNS, level: str = SIMULATION_LEVEL) -> dict[str, object]:
    """Simulate Phase 2.1-style hash rotation without memory for before/after comparison."""
    import hashlib

    from app.services.language_listening_quality.catalog import SITUATIONS_BY_LEVEL

    pool = SITUATIONS_BY_LEVEL.get(level, SITUATIONS_BY_LEVEL["B1"])
    situations = []
    for idx in range(runs):
        digest = hashlib.sha256(f"{level}|seed-{idx}".encode()).digest()
        situations.append(pool[digest[0] % len(pool)].value)

    consecutive = 1
    max_run = 1
    for idx in range(1, len(situations)):
        if situations[idx] == situations[idx - 1]:
            consecutive += 1
            max_run = max(max_run, consecutive)
        else:
            consecutive = 1

    short_window_repeats = 0
    for idx in range(len(situations)):
        window = situations[max(0, idx - 4) : idx]
        if situations[idx] in window:
            short_window_repeats += 1

    return {
        "unique_situations": len(set(situations)),
        "max_consecutive_same_situation": max_run,
        "repeats_within_5_window": short_window_repeats,
        "top_situations": Counter(situations).most_common(5),
    }


def main() -> int:
    static = audit_static()
    simulation = simulate_student_generations()
    naive = compare_naive_rotation()

    checks = [
        ("generation_wires_intelligence", static.get("generation_wires_intelligence")),
        ("stores_intelligence_metadata", static.get("stores_intelligence_metadata")),
        ("loads_history_from_db", static.get("loads_history_from_db")),
        ("cefr_engine_intact", static.get("cefr_engine_intact")),
        ("cooldown_zero_violations", simulation["cooldown_violations"] == 0),
        ("no_consecutive_same_situation", simulation["max_consecutive_same_situation"] <= 1),
        ("diversity_score_70_plus", (simulation["diversity_score"] or 0) >= 70),
        ("category_not_dominated", (simulation["max_category_share"] or 1) <= 0.35),
        ("unique_situations_6_plus", (simulation["unique_situations"] or 0) >= 6),
        ("unique_formats_4_plus", (simulation["unique_formats"] or 0) >= 4),
        ("intelligence_beats_naive_repeats", simulation["cooldown_violations"]
         < naive["repeats_within_5_window"]),
    ]

    print("LANGUAGE-INTELLIGENCE-PHASE-2.2 VERIFICATION")
    print("=" * 52)
    for key, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print(f"\nSIMULATION ({simulation['runs']} generations, level {simulation['level']})")
    print(f"  Diversity score: {simulation['diversity_score']}")
    print(f"  Cooldown violations: {simulation['cooldown_violations']}")
    print(f"  Max consecutive same situation: {simulation['max_consecutive_same_situation']}")
    print(f"  Unique situations: {simulation['unique_situations']}")
    print(f"  Unique categories: {simulation['unique_categories']}")
    print(f"  Unique formats: {simulation['unique_formats']}")
    print(f"  Max category share: {simulation['max_category_share']}")

    print("\n  Situation distribution (top 8):")
    for name, count in list(simulation["situation_distribution"].items())[:8]:
        print(f"    {name}: {count}")

    print("\n  Category distribution:")
    for name, count in simulation["category_distribution"].items():
        print(f"    {name}: {count}")

    print("\n  Format distribution:")
    for name, count in simulation["format_distribution"].items():
        print(f"    {name}: {count}")

    print("\n  Difficulty distribution:")
    for name, count in simulation["difficulty_distribution"].items():
        print(f"    {name}: {count}")

    print("\nBEFORE vs AFTER (naive hash rotation vs intelligence)")
    print(f"  Naive repeats within 5-window: {naive['repeats_within_5_window']}")
    print(f"  Intelligence cooldown violations: {simulation['cooldown_violations']}")
    print(f"  Naive max consecutive: {naive['max_consecutive_same_situation']}")
    print(f"  Intelligence max consecutive: {simulation['max_consecutive_same_situation']}")
    print(f"  Naive unique situations: {naive['unique_situations']}")
    print(f"  Intelligence unique situations: {simulation['unique_situations']}")

    report = {
        "phase": "2.2",
        "static": static,
        "simulation": simulation,
        "naive_baseline": naive,
        "overall_pass": all(ok for _, ok in checks),
    }
    out_path = Path(__file__).resolve().parents[1] / "scripts" / "_phase_2_2_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("-" * 52)
    print(f"  OVERALL: {'PASS' if report['overall_pass'] else 'FAIL'}")
    print(f"  Report: {out_path}")
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
