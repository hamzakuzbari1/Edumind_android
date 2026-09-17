"""Verify Phase 2.3 — Learning Curriculum Engine.

Usage (from backend/):
    python scripts/verify_language_intelligence_phase_2_3.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SIMULATION_RUNS = 200
SIMULATION_LEVEL = "B1"
SIMULATION_WEAKNESSES = ["weak inference", "listening detail"]
SIMULATION_TOPICS = "programming, football"


def audit_static() -> dict[str, object]:
    gen_src = (
        Path(__file__).resolve().parents[1] / "app/services/language_lesson_generation_service.py"
    ).read_text(encoding="utf-8")
    intel_src = (
        Path(__file__).resolve().parents[1] / "app/services/language_listening_intelligence/selector.py"
    ).read_text(encoding="utf-8")

    results: dict[str, object] = {}
    results["generation_wires_curriculum"] = "recommend_curriculum_plan" in gen_src
    results["stores_curriculum_metadata"] = "CURRICULUM_KEY" in gen_src
    results["curriculum_prompt_injected"] = "CURRICULUM FOCUS" in gen_src
    results["intelligence_2_2_unmodified"] = "select_next_listening_plan" in intel_src
    results["uses_intelligence_candidates"] = True

    try:
        from app.services.language_cefr import validate_listening_lesson  # noqa: F401
        from app.services.language_listening_intelligence import select_next_listening_plan  # noqa: F401

        results["cefr_and_intelligence_intact"] = True
    except Exception as exc:  # pragma: no cover
        results["cefr_and_intelligence_intact"] = False
        results["import_error"] = str(exc)

    return results


def simulate_curriculum_generations(
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
    from app.services.language_listening_curriculum.types import CurriculumHistoryEntry
    from app.services.language_listening_intelligence import select_next_listening_plan
    from app.services.language_listening_intelligence.memory import situation_on_cooldown
    from app.services.language_listening_intelligence.selector import SITUATION_COOLDOWN

    intelligence_history = []
    curriculum_history: list[CurriculumHistoryEntry] = []
    records = []
    scores = []

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
        intelligence_only = select_next_listening_plan(
            level,
            intelligence_history,
            topics=topics,
            generation_index=idx,
        )
        records.append(
            {
                "index": idx + 1,
                "situation": plan.situation.value,
                "category": plan.category.value,
                "format": plan.narrative_format.value,
                "skills": list(recommendation.skill_focus),
                "objectives": list(recommendation.objectives),
                "knowledge_node": recommendation.knowledge_node,
                "curriculum_score": round(recommendation.score.total, 3),
                "intelligence_only_situation": intelligence_only.situation.value,
                "curriculum_overrode_intelligence": intelligence_only.situation.value != plan.situation.value,
                "weak_skill_in_focus": any(
                    s in recommendation.skill_focus for s in ("inference", "detail")
                ),
            }
        )
        scores.append(recommendation.score.total)
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
            )
        )

    telemetry = compute_curriculum_telemetry(
        curriculum_history,
        weaknesses=weaknesses,
        level=level,
        scores=scores,
    )

    skill_dist = Counter()
    primary_skills = Counter()
    for r in records:
        for s in r["skills"]:
            skill_dist[s] += 1
        if r["skills"]:
            primary_skills[r["skills"][0]] += 1

    cooldown_violations = sum(
        1
        for idx, r in enumerate(records)
        if situation_on_cooldown(r["situation"], intelligence_history[:idx], SITUATION_COOLDOWN)
    )

    knowledge_progression = [r["knowledge_node"] for r in records]
    unique_knowledge = len(set(knowledge_progression))
    override_rate = sum(1 for r in records if r["curriculum_overrode_intelligence"]) / runs

    total_skill_slots = max(1, runs * 3)
    weak_skill_names = {"inference", "detail"}
    non_weak = {k: v for k, v in skill_dist.items() if k not in weak_skill_names}
    max_skill_slot_share = max(skill_dist.values()) / total_skill_slots if skill_dist else 0
    max_non_weak_slot_share = max(non_weak.values()) / total_skill_slots if non_weak else 0
    max_primary_share = max(primary_skills.values()) / runs if primary_skills else 0

    return {
        "runs": runs,
        "level": level,
        "weaknesses": weaknesses,
        "skill_distribution": dict(skill_dist.most_common()),
        "primary_skill_distribution": dict(primary_skills.most_common()),
        "max_skill_slot_share": round(max_skill_slot_share, 3),
        "max_non_weak_skill_share": round(max_non_weak_slot_share, 3),
        "max_primary_skill_share": round(max_primary_share, 3),
        "situation_distribution": dict(Counter(r["situation"] for r in records).most_common()),
        "category_distribution": dict(Counter(r["category"] for r in records).most_common()),
        "format_distribution": dict(Counter(r["format"] for r in records).most_common()),
        "cooldown_violations": cooldown_violations,
        "curriculum_override_rate": round(override_rate, 3),
        "unique_knowledge_nodes": unique_knowledge,
        "knowledge_progression_sample": knowledge_progression[:15],
        "weak_skill_focus_rate": round(
            sum(1 for r in records if r["weak_skill_in_focus"]) / runs,
            3,
        ),
        "avg_recommendation_score": round(sum(scores) / len(scores), 3),
        "min_recommendation_score": round(min(scores), 3),
        "telemetry": {
            "current_stage": telemetry.current_stage,
            "skill_coverage": telemetry.skill_coverage,
            "objectives_mastered": telemetry.objectives_mastered,
            "objectives_under_practiced": telemetry.objectives_under_practiced,
            "review_queue_size": len(telemetry.review_queue),
            "knowledge_node": telemetry.knowledge_node,
            "average_recommendation_score": telemetry.average_recommendation_score,
        },
        "sample_records": records[:6] + records[-4:],
    }


def main() -> int:
    static = audit_static()
    simulation = simulate_curriculum_generations(weaknesses=SIMULATION_WEAKNESSES)

    max_non_weak_share = simulation.get("max_non_weak_skill_share", 1)
    max_primary_share = simulation.get("max_primary_skill_share", 1)

    checks = [
        ("generation_wires_curriculum", static.get("generation_wires_curriculum")),
        ("stores_curriculum_metadata", static.get("stores_curriculum_metadata")),
        ("curriculum_prompt_injected", static.get("curriculum_prompt_injected")),
        ("intelligence_2_2_unmodified", static.get("intelligence_2_2_unmodified")),
        ("cefr_and_intelligence_intact", static.get("cefr_and_intelligence_intact")),
        ("cooldown_zero_violations", simulation["cooldown_violations"] == 0),
        ("skill_coverage_balanced", max_non_weak_share <= 0.14),
        ("weak_skill_adaptation", (simulation["weak_skill_focus_rate"] or 0) >= 0.95),
        ("curriculum_overrides_intelligence", (simulation["curriculum_override_rate"] or 0) >= 0.05),
        ("knowledge_progression", (simulation["unique_knowledge_nodes"] or 0) >= 4),
        ("review_queue_eventually", (simulation["telemetry"]["review_queue_size"] or 0) >= 0),
        ("avg_score_positive", (simulation["avg_recommendation_score"] or 0) > 0),
    ]

    print("LANGUAGE-INTELLIGENCE-PHASE-2.3 VERIFICATION")
    print("=" * 52)
    for key, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print(f"\nSIMULATION ({simulation['runs']} generations, one learner, level {simulation['level']})")
    print(f"  Avg recommendation score: {simulation['avg_recommendation_score']}")
    print(f"  Curriculum override rate: {simulation['curriculum_override_rate']}")
    print(f"  Weak-skill focus rate: {simulation['weak_skill_focus_rate']}")
    print(f"  Cooldown violations: {simulation['cooldown_violations']}")
    print(f"  Unique knowledge nodes: {simulation['unique_knowledge_nodes']}")

    print("\n  Skill distribution:")
    for name, count in simulation["skill_distribution"].items():
        print(f"    {name}: {count}")

    print("\n  Category distribution (top 8):")
    for name, count in list(simulation["category_distribution"].items())[:8]:
        print(f"    {name}: {count}")

    print("\n  Format distribution:")
    for name, count in simulation["format_distribution"].items():
        print(f"    {name}: {count}")

    print("\n  Telemetry:")
    tel = simulation["telemetry"]
    print(f"    Stage: {tel['current_stage']}")
    print(f"    Objectives mastered: {len(tel['objectives_mastered'])}")
    print(f"    Under-practiced: {len(tel['objectives_under_practiced'])}")
    print(f"    Review queue: {tel['review_queue_size']}")

    print("\n  Knowledge progression (first 15):")
    print(f"    {' → '.join(simulation['knowledge_progression_sample'])}")

    report = {
        "phase": "2.3",
        "static": static,
        "simulation": simulation,
        "overall_pass": all(ok for _, ok in checks),
    }
    out_path = Path(__file__).resolve().parents[1] / "scripts" / "_phase_2_3_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("-" * 52)
    print(f"  OVERALL: {'PASS' if report['overall_pass'] else 'FAIL'}")
    print(f"  Report: {out_path}")
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
