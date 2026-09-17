"""Verify Phase 5.3.1 — Promotion Readiness Stability Engine.

Usage (from backend/):
    python scripts/verify_language_promotion_stability_phase_5_3_1.py
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progression import LanguageProgression
from app.services.language_learning_stage import evaluate_listening_learning_stage
from app.services.language_promotion_readiness import (
    ReadinessStatus,
    evaluate_listening_promotion_readiness,
)
from app.services.language_promotion_stability import (
    PromotionPrediction,
    ReadinessHistoryEntry,
    evaluate_promotion_stability,
)
from app.services.language_promotion_stability.history import compute_rolling_stats
from app.services.language_promotion_stability.policy import DEFAULT_STABILITY_POLICY
from app.services.language_promotion_stability.scoring import confidence_to_prediction
from app.services.language_progression_service import get_official_cefr, upsert_official_levels
from app.services.language_transition_gate import evaluate_listening_transition_gate


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


def _mock_readiness(**kwargs):
    defaults = dict(
        official_cefr="A2",
        readiness_score=95,
        status=ReadinessStatus.READY,
        estimated_remaining=5.0,
        primary_blockers=(),
        secondary_blockers=(),
        strengths=("High confidence.",),
        next_actions=("Complete pending review.",),
    )
    defaults.update(kwargs)
    telemetry = SimpleNamespace(
        persistent_stage=3,
        stage_score=85,
        gate_overall_score=92.0,
        gate_eligible=True,
        dimension_scores=(),
    )
    return SimpleNamespace(**defaults, telemetry=telemetry)


def _mock_snapshot(**kwargs):
    defaults = dict(
        official_cefr="A2",
        confidence_avg=0.85,
        evidence_coverage_avg=0.75,
        objective_mastery_ratio=0.65,
        challenge_score=0.65,
        challenge_level="normal",
        demote_streak=0,
        review_completion_ratio=0.85,
        pending_review_count=0,
        recent_stability=0.75,
        lesson_index=10,
        mastered_objectives=5,
        total_objectives=8,
        review_due_objectives=(),
        needs_evidence_objectives=(),
        missing_speaker_evidence=False,
        missing_inference_evidence=False,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _history(scores: list[int], *, gate: bool = True, lesson_start: int = 1) -> list[ReadinessHistoryEntry]:
    return [
        ReadinessHistoryEntry(
            lesson_index=lesson_start + i,
            readiness_score=score,
            gate_eligible=gate,
            confidence_avg=0.82,
            evidence_coverage_avg=0.74,
            review_completion_ratio=0.82,
            recent_consistency=0.72,
            challenge_score=0.62,
        )
        for i, score in enumerate(scores)
    ]


def verify_rolling_statistics() -> list[bool]:
    print("\n=== Rolling statistics ===")
    results: list[bool] = []
    history = _history([88, 91, 90, 92, 89, 93, 90, 91, 92, 94])
    stats = compute_rolling_stats(history, policy=DEFAULT_STABILITY_POLICY)
    results.append(_ok("rolling average computed", stats.rolling_average >= 90))
    results.append(_ok("rolling minimum computed", stats.rolling_minimum == 88))
    results.append(_ok("variance non-negative", stats.rolling_variance >= 0))
    results.append(_ok("stable lessons counted", stats.stable_lessons >= 8))
    results.append(_ok("streak tracked", stats.current_streak >= 1))
    return results


def verify_single_lesson_spike() -> list[bool]:
    print("\n=== Single lesson spike ===")
    results: list[bool] = []

    spike_ready = _mock_readiness(readiness_score=100, status=ReadinessStatus.PROMOTION_AVAILABLE)
    spike_snap = _mock_snapshot(lesson_index=1)
    spike_result, _ = evaluate_promotion_stability(
        readiness=spike_ready,
        snapshot=spike_snap,
        history=[],
        policy=DEFAULT_STABILITY_POLICY,
    )
    results.append(_ok("single spike readiness 100", spike_ready.readiness_score == 100))
    results.append(
        _ok(
            "single spike confidence capped",
            spike_result.promotion_confidence < 90,
            str(spike_result.promotion_confidence),
        )
    )
    results.append(
        _ok(
            "single spike not Very Likely",
            spike_result.prediction != PromotionPrediction.VERY_LIKELY,
            spike_result.prediction.value,
        )
    )
    results.append(
        _ok(
            "smoothed below raw spike",
            spike_result.telemetry.smoothed_readiness < spike_ready.readiness_score,
            str(spike_result.telemetry.smoothed_readiness),
        )
    )
    return results


def verify_stable_learner_confidence() -> list[bool]:
    print("\n=== Stable learner confidence ===")
    results: list[bool] = []

    stable_history = _history([92, 93, 91, 94, 92, 93, 95, 92, 94, 96], lesson_start=20)
    stable_ready = _mock_readiness(readiness_score=96)
    stable_snap = _mock_snapshot(lesson_index=29)
    stable_result, _ = evaluate_promotion_stability(
        readiness=stable_ready,
        snapshot=stable_snap,
        history=stable_history,
        policy=DEFAULT_STABILITY_POLICY,
    )
    unstable_history = _history([55, 60, 58, 62, 57, 59, 61, 58, 60, 62], lesson_start=20)
    unstable_result, _ = evaluate_promotion_stability(
        readiness=_mock_readiness(readiness_score=62),
        snapshot=_mock_snapshot(lesson_index=29),
        history=unstable_history,
        policy=DEFAULT_STABILITY_POLICY,
    )

    results.append(
        _ok(
            "stable learner higher confidence",
            stable_result.promotion_confidence > unstable_result.promotion_confidence,
            f"{stable_result.promotion_confidence} vs {unstable_result.promotion_confidence}",
        )
    )
    results.append(
        _ok(
            "stable learner higher stability",
            stable_result.readiness_stability > unstable_result.readiness_stability,
        )
    )
    return results


def verify_prediction_model() -> list[bool]:
    print("\n=== Prediction model ===")
    results: list[bool] = []
    results.append(_ok("90+ Very Likely", confidence_to_prediction(92) == PromotionPrediction.VERY_LIKELY))
    results.append(_ok("75+ Likely", confidence_to_prediction(78) == PromotionPrediction.LIKELY))
    results.append(_ok("60+ Borderline", confidence_to_prediction(65) == PromotionPrediction.BORDERLINE))
    results.append(_ok("40+ Uncertain", confidence_to_prediction(45) == PromotionPrediction.UNCERTAIN))
    results.append(_ok("<40 Not Ready", confidence_to_prediction(30) == PromotionPrediction.NOT_READY))
    return results


def verify_recommendations_grounded() -> list[bool]:
    print("\n=== Recommendations ===")
    results: list[bool] = []
    ready = _mock_readiness(readiness_score=88)
    snap = _mock_snapshot(
        pending_review_count=2,
        review_due_objectives=("inference_main",),
        missing_speaker_evidence=True,
        lesson_index=3,
    )
    result, _ = evaluate_promotion_stability(
        readiness=ready,
        snapshot=snap,
        history=_history([70, 72, 75]),
        policy=DEFAULT_STABILITY_POLICY,
    )
    results.append(_ok("recommendations generated", len(result.recommendations) > 0))
    results.append(
        _ok(
            "mentions reviews or multi-speaker",
            any("review" in r.lower() or "multi-speaker" in r.lower() for r in result.recommendations),
        )
    )
    results.append(_ok("primary recommendation set", bool(result.recommendation)))
    return results


async def verify_db_unchanged() -> list[bool]:
    print("\n=== DB unchanged layers ===")
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
        saved_readiness_score = int(row.promotion_readiness_score or 0)

        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_stability_5_3_1",
            force=True,
        )
        row.learning_stage_listening = 2
        await db.flush()
        await db.refresh(row)
        baseline_listening = row.official_listening_cefr

        readiness_before = await evaluate_listening_promotion_readiness(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        gate_before = await evaluate_listening_transition_gate(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        stage_before = await evaluate_listening_learning_stage(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )

        from app.services.language_promotion_stability.engine import (
            evaluate_and_persist_listening_promotion_stability,
        )

        stability = await evaluate_and_persist_listening_promotion_stability(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        readiness_after = await evaluate_listening_promotion_readiness(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        gate_after = await evaluate_listening_transition_gate(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        stage_after = await evaluate_listening_learning_stage(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        await db.refresh(row)

        results.append(_ok("stability persisted in json", row.promotion_readiness_json.get("stability") is not None))
        results.append(
            _ok(
                "history stored",
                len((row.promotion_readiness_json.get("stability") or {}).get("history", [])) >= 1,
            )
        )
        results.append(
            _ok(
                "promotion confidence stored",
                (row.promotion_readiness_json.get("stability") or {}).get("promotion_confidence")
                == stability.promotion_confidence,
            )
        )
        results.append(_ok("learning stage unchanged", row.learning_stage_listening == 2))
        results.append(
            _ok(
                "readiness score unchanged by stability eval",
                readiness_before.readiness_score == readiness_after.readiness_score,
            )
        )
        results.append(_ok("gate eligibility unchanged", gate_before.eligible == gate_after.eligible))
        results.append(
            _ok(
                "gate score unchanged",
                gate_before.overall_gate_score == gate_after.overall_gate_score,
            )
        )
        results.append(_ok("stage eval unchanged", stage_before.current_stage == stage_after.current_stage))
        results.append(
            _ok(
                "official CEFR unchanged",
                row.official_listening_cefr == baseline_listening == LanguageLevel.A2,
            )
        )
        official = await get_official_cefr(
            db, student_id=sid, language_id=lid, skill=LanguageSkill.listening
        )
        results.append(_ok("get_official_cefr still A2", official.level == LanguageLevel.A2))

        row.learning_stage_listening = saved_stage
        row.promotion_readiness_score = saved_readiness_score
        await db.rollback()

    return results


def verify_engines_untouched() -> list[bool]:
    print("\n=== Upstream engines untouched ===")
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    packages = [
        "language_promotion_readiness",
        "language_learning_stage",
        "language_transition_gate",
        "language_listening_challenge",
    ]
    results: list[bool] = []
    for pkg in packages:
        path = root / pkg
        text_body = "\n".join(p.read_text(encoding="utf-8") for p in path.rglob("*.py"))
        results.append(
            _ok(
                f"{pkg} has no promotion_stability import",
                "language_promotion_stability" not in text_body,
            )
        )

    for mod_name in (
        "language_promotion_readiness.engine",
        "language_learning_stage.engine",
        "language_transition_gate.engine",
    ):
        import importlib

        mod = importlib.import_module(f"app.services.{mod_name}")
        src = inspect.getsource(mod)
        results.append(_ok(f"{mod_name} unchanged", "language_promotion_stability" not in src))

    return results


async def main() -> int:
    print("verify_language_promotion_stability_phase_5_3_1")
    all_results: list[bool] = []
    all_results.extend(verify_rolling_statistics())
    all_results.extend(verify_single_lesson_spike())
    all_results.extend(verify_stable_learner_confidence())
    all_results.extend(verify_prediction_model())
    all_results.extend(verify_recommendations_grounded())
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
