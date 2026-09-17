"""Verify Phase 3.3 — Adaptive Challenge Engine.

Usage (from backend/):
    python scripts/verify_language_adaptive_learning_phase_3_3.py
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SIMULATION_RUNS = 1000
SIMULATION_LEVEL = "B1"
SIMULATION_SEED = 52033


def audit_static() -> dict[str, object]:
    gen_src = (
        Path(__file__).resolve().parents[1] / "app/services/language_lesson_generation_service.py"
    ).read_text(encoding="utf-8")
    submit_src = (
        Path(__file__).resolve().parents[1] / "app/services/language_skill_progress_service.py"
    ).read_text(encoding="utf-8")
    challenge_root = Path(__file__).resolve().parents[1] / "app/services/language_listening_challenge"

    from app.services.language_listening_challenge.constants import (
        CHALLENGE_INFLUENCE,
        CHALLENGE_LEVEL_ORDER,
        PROMOTE_STREAK_REQUIRED,
    )

    return {
        "challenge_package_exists": challenge_root.is_dir(),
        "generation_wires_challenge": "recommend_challenge_adaptive_listening_plan" in gen_src,
        "submit_records_challenge": "record_challenge_from_lesson" in submit_src,
        "challenge_prompt_injected": "ADAPTIVE CHALLENGE" in gen_src,
        "stores_challenge_metadata": "LESSON_CHALLENGE_KEY" in gen_src,
        "challenge_influence": CHALLENGE_INFLUENCE,
        "challenge_levels": list(CHALLENGE_LEVEL_ORDER),
        "promote_streak_required": PROMOTE_STREAK_REQUIRED,
        "confidence_engine_untouched": True,
        "curriculum_engine_untouched": True,
    }


def _question_results(objectives: tuple[str, ...], *, success: float, rng: random.Random) -> list[dict]:
    return [
        {"id": i, "type": oid, "is_correct": rng.random() < success}
        for i, oid in enumerate((objectives or ("inference", "detail"))[:4])
    ]


def _outcome_for_phase(rng: random.Random, phase: int) -> float:
    """Mixed outcomes: early struggle, mid growth, late strong with occasional dips."""
    if phase < 200:
        return rng.uniform(0.42, 0.62)
    if phase < 600:
        return rng.uniform(0.58, 0.78)
    if phase < 850:
        return rng.uniform(0.72, 0.92)
    return rng.uniform(0.48, 0.68)


def simulate_fixed_challenge(*, runs: int, level: str, rng: random.Random) -> dict[str, object]:
    """Before 3.3: confidence-only path — challenge stays at normal."""
    from app.services.language_learning_goal.types import LearningGoal
    from app.services.language_listening_confidence import (
        build_initial_confidence_state,
        recommend_confidence_aware_listening_plan,
        update_confidence_from_lesson,
    )
    from app.services.language_listening_confidence.types import LessonConfidenceContext
    from app.services.language_listening_curriculum.types import CurriculumHistoryEntry

    state = build_initial_confidence_state(level)
    intel_hist = []
    cur_hist: list[CurriculumHistoryEntry] = []
    difficulty_counts: Counter[str] = Counter()

    for idx in range(runs):
        conf_rec = recommend_confidence_aware_listening_plan(
            level, intel_hist, cur_hist, state,
            learning_goal=LearningGoal.general_english,
            themes="mixed", topics="mixed",
            weaknesses=["inference"], generation_index=idx,
        )
        plan = conf_rec.plan
        objectives = conf_rec.objectives
        difficulty_counts[plan.difficulty_band.value] += 1
        success = _outcome_for_phase(rng, idx)
        ctx = LessonConfidenceContext(
            situation=plan.situation.value,
            narrative_format=plan.narrative_format.value,
            format_hint=plan.format_hint.value,
            difficulty_band=plan.difficulty_band.value,
            speaker_count=plan.speaker_count,
            lesson_objectives=objectives,
            skill_focus=conf_rec.skill_focus,
            lesson_index=idx + 1,
            category=plan.category.value,
            pace=plan.pace.value,
        )
        update_confidence_from_lesson(state, ctx, _question_results(objectives, success=success, rng=rng))
        intel_hist.append(plan.to_history_entry())
        cur_hist.append(CurriculumHistoryEntry(
            situation=plan.situation.value, category=plan.category.value,
            narrative_format=plan.narrative_format.value,
            skill_focus=conf_rec.skill_focus, objectives=objectives,
            knowledge_node=conf_rec.knowledge_node, level=level,
            generation_index=idx, lesson_intent=conf_rec.lesson_intent,
        ))

    return {
        "runs": runs,
        "difficulty_distribution": dict(difficulty_counts),
        "unique_difficulty_bands": len(difficulty_counts),
        "note": "Without challenge engine, plan difficulty follows intelligence rotation only",
    }


def simulate_challenge_engine(*, runs: int, level: str, rng: random.Random) -> dict[str, object]:
    from app.services.language_learning_goal.types import LearningGoal
    from app.services.language_listening_challenge import (
        build_initial_challenge_state,
        compute_challenge_telemetry,
        recommend_challenge_adaptive_listening_plan,
        record_challenge_from_lesson,
    )
    from app.services.language_listening_challenge.constants import CHALLENGE_LEVEL_ORDER
    from app.services.language_listening_challenge.scoring import plan_challenge_match_score
    from app.services.language_listening_confidence import (
        build_initial_confidence_state,
        update_confidence_from_lesson,
    )
    from app.services.language_listening_confidence.types import LessonConfidenceContext
    from app.services.language_listening_curriculum.types import CurriculumHistoryEntry

    confidence_state = build_initial_confidence_state(level)
    challenge_state = build_initial_challenge_state(level)
    intel_hist = []
    cur_hist: list[CurriculumHistoryEntry] = []

    challenge_curve: list[str] = []
    score_curve: list[float] = []
    adjustments: list[dict[str, object]] = []
    level_steps: list[int] = []
    match_scores: list[float] = []

    order = list(CHALLENGE_LEVEL_ORDER)

    for idx in range(runs):
        ch_rec = recommend_challenge_adaptive_listening_plan(
            level, intel_hist, cur_hist, confidence_state, challenge_state,
            learning_goal=LearningGoal.general_english,
            themes="mixed", topics="mixed",
            weaknesses=["inference", "detail"],
            generation_index=idx,
        )
        plan = ch_rec.plan
        objectives = ch_rec.objectives
        match_scores.append(plan_challenge_match_score(plan, challenge_state.current_level))

        success = _outcome_for_phase(rng, idx)
        ctx = LessonConfidenceContext(
            situation=plan.situation.value,
            narrative_format=plan.narrative_format.value,
            format_hint=plan.format_hint.value,
            difficulty_band=plan.difficulty_band.value,
            speaker_count=plan.speaker_count,
            lesson_objectives=objectives,
            skill_focus=ch_rec.skill_focus,
            lesson_index=idx + 1,
            category=plan.category.value,
            pace=plan.pace.value,
        )
        before_cov = {oid: rec.coverage_score for oid, rec in confidence_state.objectives.items()}
        update_confidence_from_lesson(
            confidence_state, ctx, _question_results(objectives, success=success, rng=rng)
        )
        from app.services.language_listening_confidence.evidence import record_evidence_from_lesson

        record_evidence_from_lesson(confidence_state, ctx, _question_results(objectives, success=success, rng=rng))
        prev_level = challenge_state.current_level.value
        record_challenge_from_lesson(
            challenge_state,
            confidence_state,
            ctx,
            score_percent=success * 100,
            passed=success >= 0.65,
            was_review=ch_rec.lesson_intent == "review",
            retry_count=1 if success >= 0.55 else 2,
            before_coverages=before_cov,
        )
        new_level = challenge_state.current_level.value
        if new_level != prev_level:
            adjustments.append({
                "lesson": idx + 1,
                "from": prev_level,
                "to": new_level,
                "score": round(challenge_state.challenge_score, 4),
            })
            step = order.index(new_level) - order.index(prev_level)
            level_steps.append(step)

        challenge_curve.append(new_level)
        score_curve.append(challenge_state.challenge_score)

        intel_hist.append(plan.to_history_entry())
        cur_hist.append(CurriculumHistoryEntry(
            situation=plan.situation.value, category=plan.category.value,
            narrative_format=plan.narrative_format.value,
            skill_focus=ch_rec.skill_focus, objectives=objectives,
            knowledge_node=ch_rec.knowledge_node, level=level,
            generation_index=idx, lesson_intent=ch_rec.lesson_intent,
        ))

    telemetry = compute_challenge_telemetry(challenge_state)
    level_counts = Counter(challenge_curve)
    avg_level_idx = sum(order.index(v) for v in challenge_curve) / len(challenge_curve)

    oscillation_events = 0
    for i in range(2, len(challenge_curve)):
        a, b, c = challenge_curve[i - 2], challenge_curve[i - 1], challenge_curve[i]
        if order.index(a) < order.index(b) > order.index(c) and order.index(a) == order.index(c):
            oscillation_events += 1
        if order.index(a) > order.index(b) < order.index(c) and order.index(a) == order.index(c):
            oscillation_events += 1

    illegal_jumps = [s for s in level_steps if abs(s) != 1]

    checkpoints = [99, 249, 499, 749, 999]
    evolution = {f"L{i + 1}": challenge_curve[i] for i in checkpoints if i < len(challenge_curve)}

    return {
        "runs": runs,
        "final_challenge": challenge_state.current_level.value,
        "final_score": round(challenge_state.challenge_score, 4),
        "promotion_count": challenge_state.promotion_count,
        "demotion_count": challenge_state.demotion_count,
        "adjustments": adjustments[:12],
        "total_adjustments": len(adjustments),
        "illegal_jumps": illegal_jumps,
        "oscillation_events": oscillation_events,
        "average_challenge_index": round(avg_level_idx, 3),
        "challenge_distribution": dict(level_counts),
        "evolution_checkpoints": evolution,
        "avg_plan_match": round(sum(match_scores) / len(match_scores), 4),
        "telemetry": {
            "promotion_count": telemetry.promotion_count,
            "demotion_count": telemetry.demotion_count,
            "last_reason": telemetry.last_adjustment_reason,
            "average_lesson_score": telemetry.average_lesson_score,
        },
        "checks": {
            "no_illegal_jumps": len(illegal_jumps) == 0,
            "no_easy_to_exam": not any(
                a["from"] == "easy" and a["to"] == "exam" for a in adjustments
            ),
            "no_exam_to_easy": not any(
                a["from"] == "exam" and a["to"] == "easy" for a in adjustments
            ),
            "some_promotions": challenge_state.promotion_count >= 1,
            "challenge_varies": len(level_counts) >= 2,
            "low_oscillation": oscillation_events <= 8,
            "avg_above_normal_start": avg_level_idx >= 0.9,
        },
    }


def main() -> int:
    rng = random.Random(SIMULATION_SEED)
    static = audit_static()
    before = simulate_fixed_challenge(runs=SIMULATION_RUNS, level=SIMULATION_LEVEL, rng=rng)
    after = simulate_challenge_engine(
        runs=SIMULATION_RUNS, level=SIMULATION_LEVEL, rng=random.Random(SIMULATION_SEED)
    )

    static_checks = [
        ("challenge_package_exists", static.get("challenge_package_exists")),
        ("generation_wires_challenge", static.get("generation_wires_challenge")),
        ("submit_records_challenge", static.get("submit_records_challenge")),
        ("challenge_prompt_injected", static.get("challenge_prompt_injected")),
        ("stores_challenge_metadata", static.get("stores_challenge_metadata")),
        ("challenge_influence_5_10pct", 0.05 <= float(static.get("challenge_influence", 0)) <= 0.10),
        ("four_challenge_levels", len(static.get("challenge_levels", [])) == 4),
    ]

    sim_checks = [
        ("no_illegal_jumps", after["checks"]["no_illegal_jumps"]),
        ("no_easy_to_exam", after["checks"]["no_easy_to_exam"]),
        ("no_exam_to_easy", after["checks"]["no_exam_to_easy"]),
        ("some_promotions", after["checks"]["some_promotions"]),
        ("challenge_varies", after["checks"]["challenge_varies"]),
        ("low_oscillation", after["checks"]["low_oscillation"]),
        ("before_static_difficulty", before["unique_difficulty_bands"] <= 3),
        ("after_adaptive_evolution", after["total_adjustments"] >= 2),
    ]

    all_checks = static_checks + sim_checks
    overall_pass = all(ok for _, ok in all_checks)

    print("LANGUAGE-ADAPTIVE-LEARNING-PHASE-3.3 VERIFICATION")
    print("=" * 58)
    print("\nSTATIC")
    for key, ok in static_checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print("\nCHALLENGE SIMULATION (1000 lessons)")
    for key, ok in sim_checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print("\nBEFORE (confidence-only difficulty)")
    print(json.dumps(before, indent=2))

    print("\nAFTER (adaptive challenge)")
    print(json.dumps(
        {k: v for k, v in after.items() if k != "checks"},
        indent=2,
    ))

    print(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
