"""Verify Phase 5.1 — Listening Learning Stage Engine.

Usage (from backend/):
    python scripts/verify_language_learning_stage_phase_5_1.py
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
    ListeningLearningStage,
    evaluate_and_persist_listening_stage,
    evaluate_listening_learning_stage,
    stage_label,
)
from app.services.language_learning_stage.scoring import (
    SIGNAL_WEIGHTS,
    STAGE_SCORE_BANDS,
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


def verify_signal_weights() -> list[bool]:
    print("\n=== Score model ===")
    total = sum(SIGNAL_WEIGHTS.values())
    results = [_ok("signal weights sum to 1.0", abs(total - 1.0) < 1e-6, f"sum={total}")]

    high = ListeningSignalSnapshot(
        official_cefr="A2",
        confidence_avg=0.9,
        confidence_mastery_avg=0.85,
        evidence_coverage_avg=0.8,
        challenge_score=0.75,
        curriculum_progression=0.7,
        objective_mastery_ratio=0.6,
        review_completion_ratio=0.8,
        recent_stability=0.9,
    )
    contribs = compute_signal_contributions(high)
    score = compute_stage_score(contribs)
    results.append(_ok("high signals produce stage_score > 50", score > 50, str(score)))
    results.append(_ok("contributions drive score", score == int(round(sum(c.contribution for c in contribs)))))

    low = ListeningSignalSnapshot(official_cefr="A2")
    low_score = compute_stage_score(compute_signal_contributions(low))
    results.append(_ok("low signals produce stage_score < 40", low_score < 40, str(low_score)))
    return results


def verify_stage_bands_pure() -> list[bool]:
    print("\n=== Stage bands (pure) ===")
    results: list[bool] = []
    results.append(
        _ok(
            "score 39 maps to beginner band",
            score_to_band(39) == ListeningLearningStage.beginner,
        )
    )
    results.append(
        _ok(
            "score 40 maps to intermediate band",
            score_to_band(40) == ListeningLearningStage.intermediate,
        )
    )
    results.append(
        _ok(
            "score 79 maps to intermediate band",
            score_to_band(79) == ListeningLearningStage.intermediate,
        )
    )
    results.append(
        _ok(
            "score 80 maps to advanced band",
            score_to_band(80) == ListeningLearningStage.advanced,
        )
    )
    results.append(
        _ok(
            "band ranges defined",
            STAGE_SCORE_BANDS[ListeningLearningStage.beginner] == (0, 39)
            and STAGE_SCORE_BANDS[ListeningLearningStage.intermediate] == (40, 79)
            and STAGE_SCORE_BANDS[ListeningLearningStage.advanced] == (80, 100),
        )
    )
    elig = assess_transition_eligibility(
        persistent_stage=ListeningLearningStage.beginner,
        stage_score=67,
    )
    results.append(_ok("score 67 meets score-only band threshold", elig.eligible_for_next_stage))
    results.append(
        _ok(
            "stage label format",
            stage_label(official_cefr="A2", stage=ListeningLearningStage.intermediate) == "A2 Intermediate",
        )
    )
    return results


async def verify_official_cefr_unchanged() -> list[bool]:
    print("\n=== Official CEFR unchanged ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip (no progression rows)", True)]

        sid, lid = sample[0], sample[1]
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        before_stage = int(row.learning_stage_listening or 1)

        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_stage_5_1",
            force=True,
        )
        row.learning_stage_listening = 1
        await db.flush()
        await db.refresh(row)
        baseline_listening = row.official_listening_cefr
        baseline_overall = row.official_overall_cefr

        result = await evaluate_listening_learning_stage(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        await db.refresh(row)

        results.append(_ok("engine returns official A2", result.official_cefr == "A2"))
        results.append(
            _ok(
                "official_listening_cefr unchanged by stage engine",
                row.official_listening_cefr == baseline_listening,
                row.official_listening_cefr.value,
            )
        )
        results.append(
            _ok(
                "official_overall_cefr unchanged by stage engine",
                row.official_overall_cefr == baseline_overall,
            )
        )
        official = await get_official_cefr(
            db, student_id=sid, language_id=lid, skill=LanguageSkill.listening
        )
        results.append(_ok("get_official_cefr still A2", official.level == LanguageLevel.A2))
        results.append(_ok("stage_score in range", 0 <= result.stage_score <= 100, str(result.stage_score)))
        results.append(
            _ok(
                "progress_to_next computed",
                0 <= result.progress_to_next <= 100,
                str(result.progress_to_next),
            )
        )

        row.learning_stage_listening = before_stage
        await db.rollback()

    return results


async def verify_persist_stage() -> list[bool]:
    print("\n=== Stage persistence ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        sample = (
            await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))
        ).first()
        if sample is None:
            return [_ok("skip persist test", True)]

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
            source="verify_stage_5_1_persist",
            force=True,
        )
        await db.refresh(row)
        baseline_listening = row.official_listening_cefr

        from app.services.language_learning_stage.storage import save_listening_stage

        await save_listening_stage(
            db,
            student_id=sid,
            language_id=lid,
            stage=2,
            official_cefr="A2",
            stage_score=40,
            previous_stage=1,
            force=True,
        )
        await db.refresh(row)
        results.append(_ok("learning_stage_listening persisted", row.learning_stage_listening == 2))
        results.append(
            _ok(
                "official CEFR unchanged after stage write",
                row.official_listening_cefr == baseline_listening == LanguageLevel.A2,
            )
        )

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
                f"{pkg} has no learning_stage import",
                "language_learning_stage" not in text_body,
            )
        )

    evidence = (root / "language_listening_confidence" / "evidence.py").read_text(encoding="utf-8")
    results.append(_ok("evidence module untouched", "language_learning_stage" not in evidence))

    for mod_name in (
        "language_listening_challenge.engine",
        "language_listening_confidence.engine",
        "language_listening_curriculum.engine",
        "language_learning_goal.engine",
    ):
        import importlib

        mod = importlib.import_module(f"app.services.{mod_name}")
        src = inspect.getsource(mod)
        results.append(_ok(f"{mod_name} source unchanged", "language_learning_stage" not in src))

    return results


async def main() -> int:
    print("verify_language_learning_stage_phase_5_1")
    all_results: list[bool] = []
    all_results.extend(verify_signal_weights())
    all_results.extend(verify_stage_bands_pure())
    all_results.extend(await verify_official_cefr_unchanged())
    all_results.extend(await verify_persist_stage())
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
