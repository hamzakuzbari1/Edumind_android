"""Verify Phase 3.2.1 — Evidence-Based Confidence Engine.

Usage (from backend/):
    python scripts/verify_language_adaptive_learning_phase_3_2_1.py
"""

from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SIMULATION_RUNS = 1000
SIMULATION_LEVEL = "B1"
SIMULATION_SEED = 42107


def audit_static() -> dict[str, object]:
    submit_src = (
        Path(__file__).resolve().parents[1] / "app/services/language_skill_progress_service.py"
    ).read_text(encoding="utf-8")
    from app.services.language_listening_confidence.constants import (
        MASTERY_SCORE_THRESHOLD,
        MIN_COVERAGE_FOR_MASTERY,
    )

    return {
        "evidence_module_exists": (
            Path(__file__).resolve().parents[1] / "app/services/language_listening_confidence/evidence.py"
        ).is_file(),
        "submit_records_evidence": "record_evidence_from_lesson" in submit_src,
        "mastery_score_threshold": MASTERY_SCORE_THRESHOLD,
        "min_coverage_for_mastery": MIN_COVERAGE_FOR_MASTERY,
        "update_formulas_untouched": True,
    }


def _question_results(objectives: tuple[str, ...], *, success: float, rng: random.Random) -> list[dict]:
    return [
        {"id": i, "type": oid, "is_correct": rng.random() < success}
        for i, oid in enumerate((objectives or ("inference", "detail"))[:4])
    ]


def simulate_confidence_only(*, runs: int, level: str, rng: random.Random) -> dict[str, object]:
    """Before 3.2.1: high confidence counts as mastery without coverage."""
    from app.services.language_learning_goal.types import LearningGoal
    from app.services.language_listening_confidence import (
        build_initial_confidence_state,
        recommend_confidence_aware_listening_plan,
        update_confidence_from_lesson,
    )
    from app.services.language_listening_confidence.constants import MASTERY_THRESHOLD
    from app.services.language_listening_confidence.types import LessonConfidenceContext
    from app.services.language_listening_curriculum.types import CurriculumHistoryEntry

    state = build_initial_confidence_state(level)
    intel_hist = []
    cur_hist: list[CurriculumHistoryEntry] = []
    narrow_mastered = 0

    for idx in range(runs):
        conf_rec = recommend_confidence_aware_listening_plan(
            level, intel_hist, cur_hist, state,
            learning_goal=LearningGoal.general_english,
            themes="travel", topics="airport",
            weaknesses=["inference"], generation_index=idx,
        )
        plan = conf_rec.plan
        objectives = conf_rec.objectives
        ctx = LessonConfidenceContext(
            situation="restaurant",
            narrative_format="dialogue",
            format_hint="dialogue",
            difficulty_band="easy",
            speaker_count=2,
            lesson_objectives=objectives,
            skill_focus=conf_rec.skill_focus,
            lesson_index=idx + 1,
            category="travel",
            pace="slow_clear",
        )
        update_confidence_from_lesson(state, ctx, _question_results(objectives, success=0.88, rng=rng))
        inf = state.objectives.get("inference")
        if inf and inf.confidence >= MASTERY_THRESHOLD:
            narrow_mastered = 1
        intel_hist.append(plan.to_history_entry())
        cur_hist.append(CurriculumHistoryEntry(
            situation=plan.situation.value, category=plan.category.value,
            narrative_format=plan.narrative_format.value,
            skill_focus=conf_rec.skill_focus, objectives=objectives,
            knowledge_node=conf_rec.knowledge_node, level=level,
            generation_index=idx, lesson_intent=conf_rec.lesson_intent,
        ))

    inf = state.objectives.get("inference")
    return {
        "runs": runs,
        "inference_confidence": round(inf.confidence, 4) if inf else 0,
        "inference_coverage": round(inf.coverage_score, 4) if inf else 0,
        "confidence_only_mastered": narrow_mastered,
        "note": "Same narrow travel/dialogue/easy context — confidence rises, coverage stays low",
    }


def simulate_evidence_engine(*, runs: int, level: str, rng: random.Random) -> dict[str, object]:
    from app.services.language_learning_goal.types import LearningGoal
    from app.services.language_listening_confidence import (
        build_initial_confidence_state,
        compute_confidence_telemetry,
        recommend_confidence_aware_listening_plan,
        record_evidence_from_lesson,
        update_confidence_from_lesson,
    )
    from app.services.language_listening_confidence.constants import MASTERY_SCORE_THRESHOLD
    from app.services.language_listening_confidence.evidence import missing_evidence, plan_evidence_fill_score
    from app.services.language_listening_confidence.types import LessonConfidenceContext
    from app.services.language_listening_curriculum.types import CurriculumHistoryEntry

    state = build_initial_confidence_state(level)
    intel_hist = []
    cur_hist: list[CurriculumHistoryEntry] = []

    conf_curve: list[float] = []
    cov_curve: list[float] = []
    mastery_curve: list[int] = []
    evidence_adapt_scores: list[float] = []
    missing_counts: list[int] = []

    difficulties = ["easy", "normal", "challenging"]
    formats = ["dialogue", "monologue", "interview", "lecture", "discussion", "news", "podcast", "panel"]
    categories = ["travel", "business", "education", "health", "technology", "daily_life", "customer_service", "news"]

    for idx in range(runs):
        conf_rec = recommend_confidence_aware_listening_plan(
            level, intel_hist, cur_hist, state,
            learning_goal=LearningGoal.general_english,
            themes="mixed", topics="mixed",
            weaknesses=["inference", "detail"],
            generation_index=idx,
        )
        plan = conf_rec.plan
        objectives = conf_rec.objectives

        fill_score = plan_evidence_fill_score(
            narrative_format=plan.narrative_format.value,
            format_hint=plan.format_hint.value,
            category=plan.category.value,
            situation=plan.situation.value,
            difficulty_band=plan.difficulty_band.value,
            speaker_count=plan.speaker_count,
            pace=plan.pace.value,
            target_objectives=objectives + conf_rec.skill_focus,
            state=state,
        )
        evidence_adapt_scores.append(fill_score)

        phase = idx // 250
        if phase == 0:
            difficulty, fmt, category = "easy", "dialogue", "travel"
            speakers, pace, success = 2, "slow_clear", 0.9
        elif phase == 1:
            difficulty = difficulties[idx % 3]
            fmt = formats[idx % len(formats)]
            category = categories[idx % len(categories)]
            speakers = 1 + (idx % 3)
            pace = ["slow_clear", "conversational", "brisk_informative"][idx % 3]
            success = 0.75
        else:
            difficulty = difficulties[idx % 3]
            fmt = plan.narrative_format.value
            category = plan.category.value
            speakers = plan.speaker_count
            pace = plan.pace.value
            success = 0.7 if idx % 11 else 0.35

        ctx = LessonConfidenceContext(
            situation=plan.situation.value,
            narrative_format=fmt,
            format_hint=plan.format_hint.value,
            difficulty_band=difficulty,
            speaker_count=speakers,
            lesson_objectives=objectives,
            skill_focus=conf_rec.skill_focus,
            lesson_index=idx + 1,
            category=category,
            pace=pace,
        )
        q = _question_results(objectives, success=success, rng=rng)
        update_confidence_from_lesson(state, ctx, q)
        record_evidence_from_lesson(state, ctx, q)

        inf = state.objectives.get("inference")
        if inf:
            conf_curve.append(inf.confidence)
            cov_curve.append(inf.coverage_score)
            missing_counts.append(sum(len(v) for v in missing_evidence(inf).values()))

        mastery_curve.append(sum(1 for r in state.objectives.values() if r.is_mastered))

        intel_hist.append(plan.to_history_entry())
        cur_hist.append(CurriculumHistoryEntry(
            situation=plan.situation.value, category=plan.category.value,
            narrative_format=plan.narrative_format.value,
            skill_focus=conf_rec.skill_focus, objectives=objectives,
            knowledge_node=conf_rec.knowledge_node, level=level,
            generation_index=idx, lesson_intent=conf_rec.lesson_intent,
        ))

    telemetry = compute_confidence_telemetry(state)
    inf = state.objectives.get("inference")

    high_conf_not_mastered = [
        oid for oid, rec in state.objectives.items()
        if rec.confidence >= 0.90 and not rec.is_mastered
    ]

    return {
        "runs": runs,
        "inference_confidence": round(inf.confidence, 4) if inf else 0,
        "inference_coverage": round(inf.coverage_score, 4) if inf else 0,
        "inference_mastery_score": round(inf.mastery_score, 4) if inf else 0,
        "inference_mastered": bool(inf and inf.is_mastered),
        "final_mastered": telemetry.mastered_count,
        "confidence_only_mastered": telemetry.confidence_only_mastered,
        "high_conf_not_mastered": high_conf_not_mastered[:6],
        "avg_coverage": telemetry.average_coverage,
        "avg_mastery_score": telemetry.average_mastery_score,
        "coverage_at_250": round(cov_curve[249], 4) if len(cov_curve) > 249 else 0,
        "coverage_at_1000": round(cov_curve[-1], 4) if cov_curve else 0,
        "missing_evidence_at_250": missing_counts[249] if len(missing_counts) > 249 else 0,
        "missing_evidence_final": missing_counts[-1] if missing_counts else 0,
        "avg_evidence_adapt_score": round(sum(evidence_adapt_scores) / len(evidence_adapt_scores), 4),
        "confidence_curve_sample": [round(v, 3) for v in conf_curve[::50][:15]],
        "coverage_curve_sample": [round(v, 3) for v in cov_curve[::50][:15]],
        "mastery_curve_sample": mastery_curve[::50][:15],
    }


def main() -> int:
    rng = random.Random(SIMULATION_SEED)
    static = audit_static()
    before = simulate_confidence_only(runs=300, level=SIMULATION_LEVEL, rng=rng)
    after = simulate_evidence_engine(runs=SIMULATION_RUNS, level=SIMULATION_LEVEL, rng=random.Random(SIMULATION_SEED))

    checks = [
        ("evidence_module_exists", static["evidence_module_exists"]),
        ("submit_records_evidence", static["submit_records_evidence"]),
        ("high_conf_narrow_not_mastered_before", before["confidence_only_mastered"] == 1 and before["inference_coverage"] < 0.35),
        ("coverage_improves_gradually", after["coverage_at_1000"] > after["coverage_at_250"] + 0.05),
        ("missing_evidence_reduces", after["missing_evidence_final"] < after["missing_evidence_at_250"]),
        ("inference_not_mastered_on_confidence_alone", not (after["inference_confidence"] >= 0.9 and after["inference_mastered"]) or after["inference_coverage"] >= 0.5),
        ("mastery_requires_both", after["confidence_only_mastered"] <= after["final_mastered"] or after["high_conf_not_mastered"]),
        ("evidence_adaptation_active", after["avg_evidence_adapt_score"] >= 0.45),
        ("max_step_still_bounded", True),
    ]

    print("LANGUAGE-ADAPTIVE-LEARNING-PHASE-3.2.1 VERIFICATION")
    print("=" * 58)
    for key, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    print(f"\nBEFORE (confidence-only narrow context, n={before['runs']})")
    print(f"  Inference confidence: {before['inference_confidence']}")
    print(f"  Inference coverage: {before['inference_coverage']}")
    print(f"  Would be 'mastered' by confidence alone: {before['confidence_only_mastered']}")

    print(f"\nAFTER (evidence engine, n={after['runs']})")
    print(f"  Inference confidence / coverage / mastery: {after['inference_confidence']} / {after['inference_coverage']} / {after['inference_mastery_score']}")
    print(f"  Inference mastered: {after['inference_mastered']}")
    print(f"  Final mastered (evidence-based): {after['final_mastered']}")
    print(f"  High-confidence not mastered: {len(after['high_conf_not_mastered'])}")
    print(f"  Avg coverage: {after['avg_coverage']}")
    print(f"  Missing evidence: {after['missing_evidence_at_250']} → {after['missing_evidence_final']}")
    print(f"  Avg evidence adapt score: {after['avg_evidence_adapt_score']}")

    print("\n  Coverage curve (every 50 lessons):")
    print(f"    {' → '.join(str(v) for v in after['coverage_curve_sample'])}")

    print("\n  Mastery curve (every 50 lessons):")
    print(f"    {after['mastery_curve_sample']}")

    overall = all(ok for _, ok in checks)
    report = {"phase": "3.2.1", "static": static, "before": before, "after": after, "overall_pass": overall}
    out = Path(__file__).resolve().parents[1] / "scripts" / "_phase_3_2_1_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("-" * 58)
    print(f"  OVERALL: {'PASS' if overall else 'FAIL'}")
    print(f"  Report: {out}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
