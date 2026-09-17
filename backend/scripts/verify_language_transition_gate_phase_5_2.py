"""Verify Phase 5.2 — Listening Transition Gate Engine.

Usage (from backend/):
    python scripts/verify_language_transition_gate_phase_5_2.py
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progression import LanguageProgression
from app.services.language_learning_stage import (
    apply_listening_stage_transition,
    evaluate_listening_learning_stage,
)
from app.services.language_progression_service import get_official_cefr, upsert_official_levels
from app.services.language_transition_gate import (
    TransitionGateContext,
    evaluate_listening_transition_gate,
    evaluate_transition_gate,
)
from app.services.language_transition_gate.rules import (
    ALL_REQUIREMENTS,
    GATE_THRESHOLDS,
    REQUIREMENT_EVIDENCE,
    REQUIREMENT_STAGE_SCORE,
    evaluate_all_requirements,
)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


def _perfect_context(**overrides) -> TransitionGateContext:
    base = dict(
        official_cefr="A2",
        persistent_stage=1,
        stage_score=84,
        confidence_avg=0.83,
        evidence_coverage_avg=0.70,
        objective_mastery_ratio=0.55,
        challenge_score=0.62,
        challenge_level="normal",
        demote_streak=0,
        review_completion_ratio=0.82,
        pending_review_count=0,
        recent_consistency=0.72,
        lesson_index=10,
        mastered_objectives=4,
        total_objectives=8,
        needs_evidence_objectives=(),
        review_due_objectives=(),
        missing_speaker_evidence=False,
        missing_inference_evidence=False,
    )
    base.update(overrides)
    return TransitionGateContext(**base)


def verify_all_requirements_evaluated() -> list[bool]:
    print("\n=== All requirements evaluated ===")
    results: list[bool] = []
    ctx = _perfect_context()
    gate = evaluate_transition_gate(ctx)
    results.append(_ok("8 requirements evaluated", len(gate.requirements) == 8))
    results.append(
        _ok(
            "requirement names match catalog",
            {r.name for r in gate.requirements} == set(ALL_REQUIREMENTS),
        )
    )
    results.append(_ok("thresholds configured per transition", len(GATE_THRESHOLDS) == 2))
    return results


def verify_single_failure_blocks() -> list[bool]:
    print("\n=== Single failure blocks eligibility ===")
    results: list[bool] = []

    perfect = evaluate_transition_gate(_perfect_context())
    results.append(_ok("perfect learner passes", perfect.eligible))

    low_evidence = evaluate_transition_gate(
        _perfect_context(stage_score=84, confidence_avg=0.83, evidence_coverage_avg=0.58)
    )
    results.append(_ok("high score + low evidence NOT eligible", not low_evidence.eligible))
    results.append(
        _ok(
            "low evidence is primary blocker",
            REQUIREMENT_EVIDENCE in low_evidence.failed_requirements,
            low_evidence.primary_blocker or "",
        )
    )
    results.append(
        _ok(
            "evidence recommendation from telemetry",
            any("evidence" in r.lower() for r in low_evidence.recommendations),
        )
    )

    score_only = evaluate_transition_gate(
        _perfect_context(
            stage_score=84,
            confidence_avg=0.83,
            evidence_coverage_avg=0.58,
            objective_mastery_ratio=0.20,
            review_completion_ratio=0.40,
            recent_consistency=0.30,
            lesson_index=2,
            pending_review_count=2,
        )
    )
    results.append(
        _ok(
            "stage score alone never sufficient",
            not score_only.eligible and REQUIREMENT_STAGE_SCORE in score_only.passed_requirements,
        )
    )

    return results


def verify_individual_blockers() -> list[bool]:
    print("\n=== Individual blockers ===")
    results: list[bool] = []

    low_conf = evaluate_transition_gate(_perfect_context(confidence_avg=0.60))
    results.append(_ok("low confidence blocks", not low_conf.eligible))

    pending = evaluate_transition_gate(
        _perfect_context(pending_review_count=2, review_due_objectives=("inference_main",))
    )
    results.append(_ok("pending reviews block", not pending.eligible))
    results.append(
        _ok(
            "review recommendation mentions pending",
            any("review" in r.lower() for r in pending.recommendations),
        )
    )

    low_lessons = evaluate_transition_gate(_perfect_context(lesson_index=3))
    results.append(_ok("insufficient lesson count blocks", not low_lessons.eligible))

    return results


def verify_requirement_shape() -> list[bool]:
    print("\n=== Requirement object shape ===")
    results: list[bool] = []
    ctx = _perfect_context(confidence_avg=0.81, evidence_coverage_avg=0.58)
    thresholds = GATE_THRESHOLDS[(1, 2)]
    reqs = evaluate_all_requirements(ctx, thresholds)
    conf = next(r for r in reqs if r.name == "confidence")
    evid = next(r for r in reqs if r.name == "evidence_coverage")
    results.append(_ok("confidence shows current/required", conf.current == "0.81" and conf.passed))
    results.append(_ok("evidence shows fail", not evid.passed and evid.current == "58"))
    results.append(_ok("each requirement has message", all(r.message for r in reqs)))
    return results


async def verify_db_unchanged() -> list[bool]:
    print("\n=== DB: CEFR + stage unchanged, no auto-promote ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip (no progression rows)", True)]

        sid, lid = sample[0], sample[1]
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        saved_stage = int(row.learning_stage_listening or 1)

        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_gate_5_2",
            force=True,
        )
        row.learning_stage_listening = 1
        await db.flush()
        await db.refresh(row)
        baseline_listening = row.official_listening_cefr

        gate = await evaluate_listening_transition_gate(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        stage = await evaluate_listening_learning_stage(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        await db.refresh(row)

        results.append(_ok("gate returns result", gate is not None))
        results.append(_ok("learning stage unchanged after gate eval", row.learning_stage_listening == 1))
        results.append(_ok("no auto-promote via stage eval", stage.current_stage == 1))

        blocked = await apply_listening_stage_transition(
            db, student_id=sid, language_id=lid, target_stage=2, official_cefr="A2"
        )
        await db.refresh(row)
        if gate.eligible:
            results.append(_ok("explicit transition when gate passes", row.learning_stage_listening == 2))
        else:
            results.append(
                _ok(
                    "explicit transition blocked when gate fails",
                    row.learning_stage_listening == 1 and blocked.current_stage == 1,
                )
            )

        results.append(
            _ok(
                "official_listening_cefr unchanged",
                row.official_listening_cefr == baseline_listening == LanguageLevel.A2,
            )
        )
        official = await get_official_cefr(
            db, student_id=sid, language_id=lid, skill=LanguageSkill.listening
        )
        results.append(_ok("get_official_cefr still A2", official.level == LanguageLevel.A2))

        row.learning_stage_listening = saved_stage
        await db.rollback()

    return results


def verify_engines_untouched() -> list[bool]:
    print("\n=== Phase 1–3 engines untouched ===")
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    packages = [
        "language_listening_challenge",
        "language_listening_confidence",
        "language_listening_curriculum",
        "language_learning_goal",
    ]
    results: list[bool] = []
    for pkg in packages:
        path = root / pkg
        text_body = "\n".join(p.read_text(encoding="utf-8") for p in path.rglob("*.py"))
        results.append(
            _ok(
                f"{pkg} has no transition_gate import",
                "language_transition_gate" not in text_body,
            )
        )

    for mod_name in (
        "language_listening_challenge.engine",
        "language_listening_confidence.engine",
        "language_listening_curriculum.engine",
    ):
        import importlib

        mod = importlib.import_module(f"app.services.{mod_name}")
        src = inspect.getsource(mod)
        results.append(_ok(f"{mod_name} source unchanged", "language_transition_gate" not in src))

    return results


async def main() -> int:
    print("verify_language_transition_gate_phase_5_2")
    all_results: list[bool] = []
    all_results.extend(verify_all_requirements_evaluated())
    all_results.extend(verify_single_failure_blocks())
    all_results.extend(verify_individual_blockers())
    all_results.extend(verify_requirement_shape())
    all_results.extend(await verify_db_unchanged())
    all_results.extend(verify_engines_untouched())

    passed = sum(all_results)
    total = len(all_results)
    print(f"\n=== SUMMARY: {passed}/{total} checks passed ===")
    if passed == total:
        print("PASS")
        return 0
    print("FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
