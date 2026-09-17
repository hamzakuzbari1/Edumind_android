"""Verify Phase 3.4 — Learning Path & Explainability Engine.

Usage (from backend/):
    python scripts/verify_language_adaptive_learning_phase_3_4.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SIMULATION_RUNS = 500
SIMULATION_LEVEL = "B1"
SIMULATION_SEED = 63044

MANDATORY_LESSON_FIELDS = (
    "why_this_lesson",
    "why_this_topic",
    "why_this_format",
    "why_this_difficulty",
    "why_these_questions",
    "current_focus",
    "current_goal",
    "challenge_reason",
    "confidence_reason",
    "review_reason",
    "next_recommendation",
    "teacher_note",
    "student_tip",
)


def audit_static() -> dict[str, object]:
    root = Path(__file__).resolve().parents[1] / "app/services/language_listening_explainability"
    gen_src = (
        Path(__file__).resolve().parents[1] / "app/services/language_lesson_generation_service.py"
    ).read_text(encoding="utf-8")

    return {
        "package_exists": root.is_dir(),
        "engine_module": (root / "engine.py").is_file(),
        "builder_module": (root / "builder.py").is_file(),
        "learning_path_module": (root / "learning_path.py").is_file(),
        "teacher_summary_module": (root / "teacher_summary.py").is_file(),
        "student_summary_module": (root / "student_summary.py").is_file(),
        "telemetry_module": (root / "telemetry.py").is_file(),
        "generation_untouched": "generate_listening_explainability" not in gen_src,
        "protected_engines_untouched": True,
    }


def _build_body_from_recommendation(ch_rec, *, questions: list[dict]) -> dict:
    from app.services.language_listening_intelligence import HISTORY_KEY
    from app.services.language_listening_curriculum import CURRICULUM_KEY
    from app.services.language_learning_goal import GOAL_KEY
    from app.services.language_listening_confidence import LESSON_CONFIDENCE_KEY
    from app.services.language_listening_challenge import LESSON_CHALLENGE_KEY

    plan = ch_rec.plan
    conf_rec = ch_rec.confidence_aware
    goal_rec = conf_rec.goal_aware
    rec = conf_rec.recommendation
    return {
        "level": plan.level,
        "questions": questions,
        HISTORY_KEY: plan.to_metadata(),
        CURRICULUM_KEY: rec.to_metadata(),
        GOAL_KEY: goal_rec.to_metadata() if goal_rec else {},
        LESSON_CONFIDENCE_KEY: conf_rec.to_metadata(),
        LESSON_CHALLENGE_KEY: ch_rec.to_metadata(),
    }


def _signal_tokens(body: dict) -> set[str]:
    tokens: set[str] = set()
    intel = body.get("listening_intelligence") or {}
    cur = body.get("listening_curriculum") or {}
    ch = body.get("listening_challenge_lesson") or {}

    for key in ("situation", "category", "narrative_format", "difficulty_band"):
        val = intel.get(key)
        if isinstance(val, str) and val:
            tokens.add(val.replace("_", " "))
            tokens.add(val)

    for key in ("lesson_intent", "curriculum_stage", "knowledge_node"):
        val = cur.get(key)
        if isinstance(val, str) and val:
            tokens.add(val.replace("_", " "))
            tokens.add(val)

    for obj in cur.get("objectives") or []:
        if isinstance(obj, str):
            tokens.add(obj.replace("_", " "))
            tokens.add(obj)

    for obj in cur.get("skill_focus") or []:
        if isinstance(obj, str):
            tokens.add(obj.replace("_", " "))

    cl = ch.get("challenge_level")
    if isinstance(cl, str):
        tokens.add(cl)

    for q in body.get("questions") or []:
        if isinstance(q, dict) and isinstance(q.get("type"), str):
            tokens.add(q["type"].replace("_", " "))

    return tokens


def _lesson_text_blob(lesson: dict) -> str:
    return " ".join(str(v) for v in lesson.values()).lower()


def simulate_explainability(*, runs: int, level: str, rng: random.Random) -> dict[str, object]:
    from app.services.language_learning_goal.types import LearningGoal
    from app.services.language_listening_challenge import (
        build_initial_challenge_state,
        recommend_challenge_adaptive_listening_plan,
        record_challenge_from_lesson,
    )
    from app.services.language_listening_confidence import (
        build_initial_confidence_state,
        update_confidence_from_lesson,
    )
    from app.services.language_listening_confidence.evidence import record_evidence_from_lesson
    from app.services.language_listening_confidence.types import LessonConfidenceContext
    from app.services.language_listening_curriculum.types import CurriculumHistoryEntry
    from app.services.language_listening_explainability import generate_listening_explainability

    confidence_state = build_initial_confidence_state(level)
    challenge_state = build_initial_challenge_state(level)
    intel_hist = []
    cur_hist: list[CurriculumHistoryEntry] = []

    missing_fields = 0
    hallucination_hits = 0
    grounded_hits = 0
    teacher_consistent = 0
    student_consistent = 0
    path_valid = 0
    completeness_scores: list[float] = []
    gen_times: list[float] = []

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
        success = rng.uniform(0.45, 0.88)
        q_results = [
            {"id": i, "type": oid, "is_correct": rng.random() < success}
            for i, oid in enumerate(objectives[:4])
        ]
        questions = [{"type": oid, "stem": "?", "choices": ["A", "B"], "correct_index": 0} for oid in objectives[:3]]

        body = _build_body_from_recommendation(ch_rec, questions=questions)
        result = generate_listening_explainability(
            body,
            confidence_state=confidence_state,
            challenge_state=challenge_state,
            cefr_level=level,
            weak_skills=["inference"],
        )

        lesson = result.lesson.to_dict()
        for field in MANDATORY_LESSON_FIELDS:
            if not str(lesson.get(field, "")).strip():
                missing_fields += 1

        tokens = _signal_tokens(body)
        blob = _lesson_text_blob(lesson)
        matched = sum(1 for t in tokens if t.lower() in blob)
        if matched >= 2:
            grounded_hits += 1
        else:
            hallucination_hits += 1

        intel = body["listening_intelligence"]
        ch_meta = body["listening_challenge_lesson"]
        if str(ch_meta.get("challenge_level", "")).lower() in result.lesson.challenge_reason.lower():
            teacher_consistent += 1
        if str(intel.get("situation", "")).replace("_", " ") in result.student_summary.why_today_matters.lower():
            student_consistent += 1

        if result.learning_path.objectives:
            path_valid += 1
            for entry in result.learning_path.objectives:
                rec = confidence_state.objectives.get(entry.objective_id)
                if rec and rec.is_mastered and entry.status != "Mastered":
                    path_valid -= 1
                    break

        completeness_scores.append(result.telemetry.coverage_completeness)
        gen_times.append(result.telemetry.generation_time_ms)

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
        update_confidence_from_lesson(confidence_state, ctx, q_results)
        record_evidence_from_lesson(confidence_state, ctx, q_results)
        record_challenge_from_lesson(
            challenge_state,
            confidence_state,
            ctx,
            score_percent=success * 100,
            passed=success >= 0.65,
            was_review=ch_rec.lesson_intent == "review",
            retry_count=1,
            before_coverages=before_cov,
        )

        intel_hist.append(plan.to_history_entry())
        cur_hist.append(CurriculumHistoryEntry(
            situation=plan.situation.value,
            category=plan.category.value,
            narrative_format=plan.narrative_format.value,
            skill_focus=ch_rec.skill_focus,
            objectives=objectives,
            knowledge_node=ch_rec.knowledge_node,
            level=level,
            generation_index=idx,
            lesson_intent=ch_rec.lesson_intent,
        ))

    return {
        "runs": runs,
        "missing_mandatory_fields": missing_fields,
        "grounded_explanations": grounded_hits,
        "weak_grounding": hallucination_hits,
        "teacher_summary_consistent": teacher_consistent,
        "student_summary_consistent": student_consistent,
        "learning_path_valid": path_valid,
        "avg_coverage_completeness": round(sum(completeness_scores) / len(completeness_scores), 4),
        "avg_generation_ms": round(sum(gen_times) / len(gen_times), 3),
        "checks": {
            "no_missing_fields": missing_fields == 0,
            "high_grounding_rate": grounded_hits >= runs * 0.95,
            "teacher_consistency": teacher_consistent >= runs * 0.90,
            "student_consistency": student_consistent >= runs * 0.85,
            "learning_path_correct": path_valid >= runs * 0.98,
            "signal_coverage": sum(completeness_scores) / len(completeness_scores) >= 0.85,
        },
    }


def main() -> int:
    rng = random.Random(SIMULATION_SEED)
    static = audit_static()
    sim = simulate_explainability(runs=SIMULATION_RUNS, level=SIMULATION_LEVEL, rng=rng)

    static_checks = [
        ("package_exists", static.get("package_exists")),
        ("engine_module", static.get("engine_module")),
        ("builder_module", static.get("builder_module")),
        ("learning_path_module", static.get("learning_path_module")),
        ("teacher_summary_module", static.get("teacher_summary_module")),
        ("student_summary_module", static.get("student_summary_module")),
        ("telemetry_module", static.get("telemetry_module")),
        ("generation_untouched", static.get("generation_untouched")),
    ]

    sim_checks = [
        ("no_missing_fields", sim["checks"]["no_missing_fields"]),
        ("high_grounding_rate", sim["checks"]["high_grounding_rate"]),
        ("teacher_consistency", sim["checks"]["teacher_consistency"]),
        ("student_consistency", sim["checks"]["student_consistency"]),
        ("learning_path_correct", sim["checks"]["learning_path_correct"]),
        ("signal_coverage", sim["checks"]["signal_coverage"]),
    ]

    overall_pass = all(ok for _, ok in static_checks + sim_checks)

    print("LANGUAGE-ADAPTIVE-LEARNING-PHASE-3.4 VERIFICATION")
    print("=" * 58)
    print("\nSTATIC")
    for key, ok in static_checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print("\nEXPLAINABILITY SIMULATION (500 lessons)")
    for key, ok in sim_checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print("\nSIMULATION METRICS")
    print(json.dumps({k: v for k, v in sim.items() if k != "checks"}, indent=2))

    print(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
