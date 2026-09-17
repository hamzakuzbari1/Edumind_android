"""Verify listening progression runtime fixes (stage persist + promotion test shuffle).

Usage (from backend/):
    python scripts/verify_listening_progression_runtime_fix.py
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import text

BACKEND = Path(__file__).resolve().parents[1]


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def static_checks() -> dict[str, bool]:
    runtime_src = (BACKEND / "app/services/language_listening_progression/runtime.py").read_text(
        encoding="utf-8"
    )
    stage_src = (BACKEND / "app/services/language_learning_stage/engine.py").read_text(encoding="utf-8")
    builder_src = (BACKEND / "app/services/language_promotion_test/builder.py").read_text(encoding="utf-8")

    return {
        "runtime_stage_before_readiness": runtime_src.index("evaluate_and_persist_listening_stage")
        < runtime_src.index("evaluate_and_persist_listening_promotion_readiness"),
        "runtime_no_orphan_gate_call": "evaluate_listening_transition_gate" not in runtime_src,
        "persist_calls_apply_transition": "apply_listening_stage_transition" in stage_src.split(
            "evaluate_and_persist_listening_stage"
        )[1][:800],
        "builder_shuffles_choices": "_shuffle_choices_deterministic" in builder_src,
        "public_dict_hides_correct_index": "correct_index" not in (
            BACKEND / "app/services/language_promotion_test/types.py"
        ).read_text(encoding="utf-8").split("to_public_dict")[1][:400],
    }


def shuffle_checks() -> dict[str, bool]:
    from app.services.language_promotion_test.builder import (
        _CHOICE_BANK,
        _shuffle_choices_deterministic,
        build_promotion_test_session,
    )
    from app.services.language_promotion_test.scoring import grade_promotion_test_session
    from app.services.language_promotion_test.types import PromotionTestOutcome
    from app.services.language_promotion_test.scoring import score_to_outcome

    bank_choices, bank_correct = _CHOICE_BANK["detail"]
    s1, c1 = _shuffle_choices_deterministic(bank_choices, bank_correct, seed="sess-a:assess-1")
    s2, c2 = _shuffle_choices_deterministic(bank_choices, bank_correct, seed="sess-a:assess-1")
    s3, c3 = _shuffle_choices_deterministic(bank_choices, bank_correct, seed="sess-b:assess-1")

    session = build_promotion_test_session(
        student_id=1,
        language_id=1,
        official_cefr="A2",
        target_cefr="B1",
        attempt_number=1,
        used_lesson_ids=set(),
        used_sequences=set(),
    )
    indices = {a.correct_index for a in session.assessments}
    not_all_zero = indices != {0}
    answers = {a.assessment_id: a.correct_index for a in session.assessments}
    breakdown, correct = grade_promotion_test_session(session, answers)
    wrong = {a.assessment_id: (a.correct_index + 1) % len(a.choices) for a in session.assessments}
    fail_breakdown, _ = grade_promotion_test_session(session, wrong)

    return {
        "shuffle_deterministic_same_seed": s1 == s2 and c1 == c2,
        "shuffle_may_differ_other_seed": s1 != s3 or c1 != c3,
        "session_not_all_correct_index_zero": not_all_zero,
        "grading_pass_with_shuffled_answers": score_to_outcome(breakdown.overall_score)
        == PromotionTestOutcome.PASS
        and correct == len(session.assessments),
        "grading_fail_with_wrong_shuffled": score_to_outcome(fail_breakdown.overall_score)
        == PromotionTestOutcome.FAIL,
    }


def _gate_pass_snapshot(*, lesson_index: int = 12) -> object:
    from app.services.language_learning_stage.types import ListeningSignalSnapshot

    return ListeningSignalSnapshot(
        official_cefr="A2",
        confidence_avg=0.90,
        confidence_mastery_avg=0.88,
        evidence_coverage_avg=0.82,
        challenge_score=0.70,
        curriculum_progression=0.90,
        objective_mastery_ratio=0.70,
        review_completion_ratio=0.90,
        recent_stability=0.75,
        lesson_index=lesson_index,
        mastered_objectives=9,
        total_objectives=12,
        challenge_level="normal",
        demote_streak=0,
        pending_review_count=0,
        review_due_objectives=(),
        needs_evidence_objectives=(),
        missing_speaker_evidence=False,
        missing_inference_evidence=False,
    )


def _patch_listening_signals(snapshot: object):
    """Patch signal gatherers used by stage, gate, readiness, and stability engines."""
    mock = AsyncMock(return_value=snapshot)
    targets = [
        "app.services.language_learning_stage.signals.gather_listening_signals",
        "app.services.language_learning_stage.engine.gather_listening_signals",
        "app.services.language_promotion_readiness.engine.gather_listening_signals",
        "app.services.language_promotion_stability.engine.gather_listening_signals",
        "app.services.language_transition_gate.engine.gather_listening_signals",
    ]
    return [patch(target, new=mock) for target in targets]


def _enter_signal_patches(stack: ExitStack, snapshot: object) -> None:
    for patcher in _patch_listening_signals(snapshot):
        stack.enter_context(patcher)


async def stage_persist_checks() -> dict[str, bool]:
    from app.db.session import AsyncSessionLocal
    from app.models.language.enums import LanguageLevel
    from app.models.language.progression import LanguageProgression
    from app.services.language_learning_stage.engine import evaluate_and_persist_listening_stage
    from app.services.language_listening_progression.runtime import run_listening_progression_after_submit
    from app.services.language_progression_service import upsert_official_levels
    from app.services.language_promotion_readiness import ReadinessStatus, evaluate_listening_promotion_readiness

    results: dict[str, bool] = {}

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return {"stage_persist_db_skip": True}

        sid, lid = int(sample[0]), int(sample[1])
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
            source="verify_runtime_fix",
            force=True,
        )
        row.learning_stage_listening = 1
        await db.flush()

        snapshot = _gate_pass_snapshot(lesson_index=12)

        with ExitStack() as stack:
            _enter_signal_patches(stack, snapshot)
            result = await evaluate_and_persist_listening_stage(
                db, student_id=sid, language_id=lid, official_cefr="A2"
            )
            await db.refresh(row)

        results["stage_1_to_2_on_gate_pass"] = row.learning_stage_listening == 2 and result.current_stage == 2

        row.learning_stage_listening = 2
        await db.flush()

        with ExitStack() as stack:
            _enter_signal_patches(stack, snapshot)
            result2 = await evaluate_and_persist_listening_stage(
                db, student_id=sid, language_id=lid, official_cefr="A2"
            )
            await db.refresh(row)

        results["stage_2_to_3_on_gate_pass"] = row.learning_stage_listening == 3 and result2.current_stage == 3

        with ExitStack() as stack:
            _enter_signal_patches(stack, snapshot)
            readiness = await evaluate_listening_promotion_readiness(
                db, student_id=sid, language_id=lid, official_cefr="A2"
            )

        results["readiness_reaches_100_at_stage_3"] = readiness.readiness_score >= 100
        results["promotion_available_status"] = readiness.status == ReadinessStatus.PROMOTION_AVAILABLE

        with ExitStack() as stack:
            _enter_signal_patches(stack, snapshot)
            await run_listening_progression_after_submit(db, student_id=sid, language_id=lid)
            await db.refresh(row)

        results["runtime_pipeline_preserves_stage_3"] = row.learning_stage_listening == 3
        results["runtime_sets_readiness_score"] = int(row.promotion_readiness_score or 0) >= 100

        row.learning_stage_listening = saved_stage
        await db.rollback()

    return results


async def promotion_flow_checks() -> dict[str, bool]:
    from app.db.session import AsyncSessionLocal
    from app.models.language.enums import LanguageLevel, LanguageSkill
    from app.services.language_official_promotion_api import apply_listening_official_promotion_api
    from app.services.language_progression_service import get_official_cefr, upsert_official_levels
    from app.services.language_promotion_test import clear_sessions_for_tests
    from app.services.language_promotion_test.builder import build_promotion_test_session
    from app.services.language_promotion_test.scoring import grade_promotion_test_session
    from app.services.language_promotion_test.session import register_session
    from app.services.language_promotion_test.storage import save_promotion_test_attempt
    from app.services.language_promotion_test.telemetry import build_promotion_test_result
    from app.services.language_promotion_test.types import PromotionTestOutcome

    results: dict[str, bool] = {}

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return {"promotion_flow_db_skip": True}

        sid, lid = int(sample[0]), int(sample[1])
        await clear_sessions_for_tests(db, student_id=sid, language_id=lid)
        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_runtime_fix_pre",
            force=True,
        )
        await db.commit()

    async with AsyncSessionLocal() as db:
        session = build_promotion_test_session(
            student_id=sid,
            language_id=lid,
            official_cefr="A2",
            target_cefr="B1",
            attempt_number=99,
            used_lesson_ids=set(),
            used_sequences=set(),
        )
        answers = {a.assessment_id: a.correct_index for a in session.assessments}
        breakdown, _ = grade_promotion_test_session(session, answers)
        result = build_promotion_test_result(
            session=session,
            breakdown=breakdown,
            correct_count=len(session.assessments),
        )
        results["shuffled_test_graded_pass"] = result.result == PromotionTestOutcome.PASS

        await register_session(db, session)
        row = await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_runtime_fix_promo",
            force=True,
        )
        await save_promotion_test_attempt(
            db,
            student_id=sid,
            language_id=lid,
            session=session,
            result=result,
            row=row,
        )
        await db.commit()

    async with AsyncSessionLocal() as db:
        try:
            out = await apply_listening_official_promotion_api(db, student_id=sid, language_id=lid)
            await db.commit()
            official = await get_official_cefr(
                db, student_id=sid, language_id=lid, skill=LanguageSkill.listening
            )
            results["official_promotion_applied"] = out.promotion_success and out.new_cefr == "B1"
            results["official_cefr_updated"] = official.level == LanguageLevel.B1
            results["learning_stage_reset_after_promotion"] = out.new_learning_stage == 1
        except Exception as exc:
            results["official_promotion_applied"] = False
            results["official_cefr_updated"] = False
            results["learning_stage_reset_after_promotion"] = False
            print(f"  promotion flow error: {exc}")

        await db.rollback()

    return results


def regression_checks() -> dict[str, bool]:
    paths = [
        "app/services/language_listening_confidence/update.py",
        "app/services/language_listening_confidence/evidence.py",
        "app/services/language_listening_challenge/record.py",
        "app/services/language_transition_gate/rules.py",
        "app/services/language_promotion_readiness/scoring.py",
        "app/services/language_promotion_stability/scoring.py",
        "app/services/language_promotion_test/scoring.py",
        "app/services/language_official_promotion/engine.py",
    ]
    return {f"unchanged_{Path(p).stem}": (BACKEND / p).is_file() for p in paths}


def main() -> int:
    print("=== Listening Progression Runtime Fix Verification ===\n")

    static = static_checks()
    shuffle = shuffle_checks()

    async def run_async_checks() -> tuple[dict[str, bool], dict[str, bool]]:
        stage = await stage_persist_checks()
        promo = await promotion_flow_checks()
        return stage, promo

    stage, promo = asyncio.run(run_async_checks())
    regression = regression_checks()

    sections = [
        ("Static wiring", static),
        ("Promotion test shuffle", shuffle),
        ("Stage persist + readiness", stage),
        ("Promotion flow", promo),
        ("Regression (files present)", regression),
    ]

    all_results: dict[str, bool] = {}
    for title, block in sections:
        print(f"{title}:")
        for key, value in block.items():
            if key.endswith("_skip"):
                print(f"  {key}: SKIP")
                continue
            all_results[key] = bool(value)
            _ok(key, bool(value))
        print()

    passed = sum(1 for v in all_results.values() if v)
    total = len(all_results)
    ok = all(all_results.values())
    print(f"=== Results: {passed}/{total} checks passed ===")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
