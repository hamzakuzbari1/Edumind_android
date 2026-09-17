"""Verify Phase 5.1.1 — persistent stage + eligibility (no auto-promote/demotion).

Usage (from backend/):
    python scripts/verify_language_learning_stage_phase_5_1_1.py
"""

from __future__ import annotations

import asyncio
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
    ListeningLearningStage,
    apply_listening_stage_transition,
    evaluate_and_persist_listening_stage,
    evaluate_listening_learning_stage,
)
from app.services.language_learning_stage.scoring import (
    assess_transition_eligibility,
    compute_signal_contributions,
    compute_stage_score,
    score_to_band,
)
from app.services.language_learning_stage.types import ListeningSignalSnapshot
from app.services.language_progression_service import get_official_cefr, upsert_official_levels


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


def verify_score_band_eligibility_pure() -> list[bool]:
    print("\n=== Eligibility (pure) ===")
    results: list[bool] = []

    not_elig = assess_transition_eligibility(
        persistent_stage=ListeningLearningStage.beginner,
        stage_score=39,
    )
    results.append(_ok("score 39 not eligible (below 40)", not not_elig.eligible_for_next_stage))

    elig = assess_transition_eligibility(
        persistent_stage=ListeningLearningStage.beginner,
        stage_score=40,
    )
    results.append(_ok("score 40 eligible beginner->intermediate", elig.eligible_for_next_stage))

    mid_not = assess_transition_eligibility(
        persistent_stage=ListeningLearningStage.intermediate,
        stage_score=79,
    )
    results.append(_ok("score 79 not eligible intermediate->advanced", not mid_not.eligible_for_next_stage))

    mid_elig = assess_transition_eligibility(
        persistent_stage=ListeningLearningStage.intermediate,
        stage_score=80,
    )
    results.append(_ok("score 80 eligible intermediate->advanced", mid_elig.eligible_for_next_stage))

    adv = assess_transition_eligibility(
        persistent_stage=ListeningLearningStage.advanced,
        stage_score=100,
    )
    results.append(_ok("advanced has no next stage", adv.next_stage is None))
    results.append(_ok("advanced not eligible", not adv.eligible_for_next_stage))

    return results


def verify_score_changes_without_stage_change() -> list[bool]:
    print("\n=== Score changes without stage change (pure) ===")
    results: list[bool] = []

    band_low = score_to_band(25)
    results.append(
        _ok(
            "score 25 -> beginner band",
            band_low == ListeningLearningStage.beginner,
        )
    )

    band_high = score_to_band(67)
    elig_high = assess_transition_eligibility(
        persistent_stage=ListeningLearningStage.beginner,
        stage_score=67,
    )
    results.append(
        _ok(
            "persistent beginner + score 67 -> band intermediate, eligible",
            band_high == ListeningLearningStage.intermediate and elig_high.eligible_for_next_stage,
        )
    )

    band_drop = score_to_band(25)
    elig_drop = assess_transition_eligibility(
        persistent_stage=ListeningLearningStage.intermediate,
        stage_score=25,
    )
    results.append(
        _ok(
            "persistent intermediate + score 25 -> band beginner, current stage unchanged, not eligible for advanced",
            band_drop == ListeningLearningStage.beginner
            and not elig_drop.eligible_for_next_stage
            and elig_drop.next_stage == int(ListeningLearningStage.advanced),
            f"next={elig_drop.next_stage}",
        )
    )

    return results


async def verify_result_fields() -> list[bool]:
    print("\n=== LearningStageResult fields ===")
    results: list[bool] = []

    snap = ListeningSignalSnapshot(
        official_cefr="A2",
        confidence_avg=0.85,
        confidence_mastery_avg=0.8,
        evidence_coverage_avg=0.75,
        challenge_score=0.7,
        curriculum_progression=0.65,
        objective_mastery_ratio=0.55,
        review_completion_ratio=0.7,
        recent_stability=0.8,
    )
    from app.services.language_learning_stage.engine import _build_result_from_signals

    result = _build_result_from_signals(
        official_cefr="A2",
        persistent_stage=1,
        snapshot=snap,
    )
    required = (
        hasattr(result, "current_stage"),
        hasattr(result, "stage_score"),
        hasattr(result, "stage_band"),
        hasattr(result, "eligible_for_next_stage"),
        hasattr(result, "next_stage"),
        hasattr(result, "transition_requirements"),
        hasattr(result, "progress_to_next"),
    )
    results.append(_ok("LearningStageResult has required fields", all(required)))
    results.append(
        _ok(
            "current_stage equals persistent (not band)",
            result.current_stage == 1,
            f"band={result.stage_band}",
        )
    )
    results.append(_ok("transition_requirements non-empty when next exists", len(result.transition_requirements) > 0))

    return results


async def verify_no_auto_promote_db() -> list[bool]:
    print("\n=== No auto-promote / no demotion (DB) ===")
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
            source="verify_stage_5_1_1",
            force=True,
        )
        row.learning_stage_listening = 1
        await db.flush()
        await db.refresh(row)
        baseline_listening = row.official_listening_cefr

        result = await evaluate_and_persist_listening_stage(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        await db.refresh(row)

        results.append(_ok("evaluate does not auto-promote stored stage", row.learning_stage_listening == 1))
        results.append(
            _ok(
                "stage_score computed independently",
                0 <= result.stage_score <= 100,
                str(result.stage_score),
            )
        )
        if result.stage_score >= 40:
            results.append(
                _ok(
                    "score in next band does not auto-promote stored stage",
                    result.current_stage == 1,
                )
            )
            results.append(
                _ok(
                    "gate blocks score-only eligibility (5.2)",
                    not result.eligible_for_next_stage,
                    result.eligibility_reason[:60],
                )
            )
        else:
            results.append(_ok("eligible flag matches score band", not result.eligible_for_next_stage))

        row.learning_stage_listening = 2
        await db.flush()
        result_demote = await evaluate_listening_learning_stage(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        await db.refresh(row)
        results.append(
            _ok(
                "score drop does not demote persistent intermediate",
                row.learning_stage_listening == 2 and result_demote.current_stage == 2,
                f"band={result_demote.stage_band}",
            )
        )

        if result.eligible_for_next_stage:
            row.learning_stage_listening = 1
            await db.flush()
            promoted = await apply_listening_stage_transition(
                db,
                student_id=sid,
                language_id=lid,
                target_stage=2,
                official_cefr="A2",
            )
            await db.refresh(row)
            results.append(
                _ok(
                    "explicit transition promotes when eligible",
                    row.learning_stage_listening == 2 and promoted.current_stage == 2,
                )
            )
        else:
            row.learning_stage_listening = 1
            await db.flush()
            forced = await apply_listening_stage_transition(
                db,
                student_id=sid,
                language_id=lid,
                target_stage=2,
                official_cefr="A2",
            )
            await db.refresh(row)
            results.append(
                _ok(
                    "explicit transition blocked when not eligible",
                    row.learning_stage_listening == 1 and forced.current_stage == 1,
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


async def main() -> int:
    print("verify_language_learning_stage_phase_5_1_1")
    all_results: list[bool] = []
    all_results.extend(verify_score_band_eligibility_pure())
    all_results.extend(verify_score_changes_without_stage_change())
    all_results.extend(await verify_result_fields())
    all_results.extend(await verify_no_auto_promote_db())

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
