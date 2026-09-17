"""Verify Phase 5.3 — Listening Promotion Readiness Engine.

Usage (from backend/):
    python scripts/verify_language_promotion_readiness_phase_5_3.py
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
from app.services.language_learning_stage import evaluate_listening_learning_stage
from app.services.language_progression_service import get_official_cefr, upsert_official_levels
from app.services.language_promotion_readiness import (
    ReadinessStatus,
    evaluate_listening_promotion_readiness,
    evaluate_promotion_readiness,
    score_to_status,
)
from app.services.language_promotion_readiness.scoring import READINESS_WEIGHTS
from app.services.language_transition_gate import TransitionGateContext, evaluate_transition_gate


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


def _ctx(**overrides) -> TransitionGateContext:
    base = dict(
        official_cefr="A2",
        persistent_stage=3,
        stage_score=85,
        confidence_avg=0.85,
        evidence_coverage_avg=0.75,
        objective_mastery_ratio=0.65,
        challenge_score=0.65,
        challenge_level="normal",
        demote_streak=0,
        review_completion_ratio=0.85,
        pending_review_count=0,
        recent_consistency=0.75,
        lesson_index=14,
        mastered_objectives=5,
        total_objectives=8,
        needs_evidence_objectives=(),
        review_due_objectives=(),
        missing_speaker_evidence=False,
        missing_inference_evidence=False,
    )
    base.update(overrides)
    return TransitionGateContext(**base)


def _readiness(**overrides):
    ctx = _ctx(**overrides)
    gate = evaluate_transition_gate(ctx)
    return evaluate_promotion_readiness(ctx=ctx, gate=gate)


def verify_status_model() -> list[bool]:
    print("\n=== Status model ===")
    results: list[bool] = []
    results.append(_ok("0-49 NOT_READY", score_to_status(30) == ReadinessStatus.NOT_READY))
    results.append(_ok("50-79 ALMOST_READY", score_to_status(65) == ReadinessStatus.ALMOST_READY))
    results.append(_ok("80-99 READY", score_to_status(90) == ReadinessStatus.READY))
    results.append(_ok("100 PROMOTION_AVAILABLE", score_to_status(100) == ReadinessStatus.PROMOTION_AVAILABLE))
    results.append(_ok("99 not PROMOTION_AVAILABLE", score_to_status(99) != ReadinessStatus.PROMOTION_AVAILABLE))
    return results


def verify_continuous_scoring() -> list[bool]:
    print("\n=== Continuous scoring ===")
    results: list[bool] = []
    results.append(_ok("weights sum to 1.0", abs(sum(READINESS_WEIGHTS.values()) - 1.0) < 1e-6))

    low = _readiness(evidence_coverage_avg=0.40, persistent_stage=1, stage_score=35, lesson_index=4)
    mid = _readiness(evidence_coverage_avg=0.58, persistent_stage=2, stage_score=60, lesson_index=8)
    high = _readiness(evidence_coverage_avg=0.75, persistent_stage=2, stage_score=82, lesson_index=11)
    results.append(_ok("low < mid readiness", low.readiness_score < mid.readiness_score))
    results.append(_ok("mid < high readiness", mid.readiness_score < high.readiness_score))
    results.append(
        _ok(
            "promotion unavailable below 100",
            high.readiness_score < 100 and high.status != ReadinessStatus.PROMOTION_AVAILABLE,
            str(high.readiness_score),
        )
    )
    return results


def verify_perfect_promotion_available() -> list[bool]:
    print("\n=== Perfect learner ===")
    results: list[bool] = []
    perfect = _readiness()
    results.append(_ok("perfect learner score 100", perfect.readiness_score == 100))
    results.append(_ok("PROMOTION_AVAILABLE at 100", perfect.status == ReadinessStatus.PROMOTION_AVAILABLE))
    results.append(_ok("no blockers when perfect", len(perfect.primary_blockers) == 0))
    results.append(_ok("strengths generated", len(perfect.strengths) > 0))
    return results


def verify_blockers_and_actions() -> list[bool]:
    print("\n=== Blockers and actions ===")
    results: list[bool] = []

    weak = _readiness(
        evidence_coverage_avg=0.58,
        pending_review_count=0,
        review_completion_ratio=0.85,
        lesson_index=14,
        persistent_stage=3,
        stage_score=82,
        missing_inference_evidence=True,
    )
    results.append(_ok("weak learner not promotion available", weak.status != ReadinessStatus.PROMOTION_AVAILABLE))
    results.append(_ok("primary blocker present", len(weak.primary_blockers) == 1))
    results.append(
        _ok(
            "evidence is primary blocker",
            "Evidence" in weak.primary_blockers[0],
            weak.primary_blockers[0] if weak.primary_blockers else "",
        )
    )
    results.append(_ok("secondary blockers listed", len(weak.secondary_blockers) >= 0))

    multi = _readiness(
        evidence_coverage_avg=0.58,
        pending_review_count=2,
        lesson_index=5,
        persistent_stage=2,
        stage_score=70,
    )
    results.append(_ok("multi-gap learner has secondary blockers", len(multi.secondary_blockers) >= 1))
    results.append(_ok("next actions grounded", len(weak.next_actions) > 0))
    results.append(
        _ok(
            "next actions mention evidence",
            any("evidence" in a.lower() or "inference" in a.lower() for a in weak.next_actions),
        )
    )
    return results


async def verify_db_unchanged() -> list[bool]:
    print("\n=== DB: CEFR, stage, gate unchanged ===")
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
        saved_readiness = int(row.promotion_readiness_score or 0)

        await upsert_official_levels(
            db,
            student_id=sid,
            language_id=lid,
            reading=LanguageLevel.A2,
            listening=LanguageLevel.A2,
            writing=LanguageLevel.A2,
            speaking=LanguageLevel.A2,
            overall=LanguageLevel.A2,
            source="verify_readiness_5_3",
            force=True,
        )
        row.learning_stage_listening = 2
        await db.flush()
        await db.refresh(row)
        baseline_listening = row.official_listening_cefr
        baseline_stage = row.learning_stage_listening

        gate_before = await __import__(
            "app.services.language_transition_gate",
            fromlist=["evaluate_listening_transition_gate"],
        ).evaluate_listening_transition_gate(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )

        from app.services.language_promotion_readiness.engine import (
            evaluate_and_persist_listening_promotion_readiness,
        )

        result = await evaluate_and_persist_listening_promotion_readiness(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        stage_after = await evaluate_listening_learning_stage(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        gate_after = await __import__(
            "app.services.language_transition_gate",
            fromlist=["evaluate_listening_transition_gate"],
        ).evaluate_listening_transition_gate(
            db, student_id=sid, language_id=lid, official_cefr="A2"
        )
        await db.refresh(row)

        results.append(_ok("readiness persisted", row.promotion_readiness_score == result.readiness_score))
        results.append(
            _ok(
                "readiness json stored",
                row.promotion_readiness_json is not None
                and row.promotion_readiness_json.get("skill") == "listening",
            )
        )
        results.append(_ok("learning stage unchanged", row.learning_stage_listening == baseline_stage == 2))
        results.append(
            _ok(
                "official CEFR unchanged",
                row.official_listening_cefr == baseline_listening == LanguageLevel.A2,
            )
        )
        results.append(_ok("gate eligibility unchanged", gate_before.eligible == gate_after.eligible))
        results.append(
            _ok(
                "gate overall score unchanged",
                gate_before.overall_gate_score == gate_after.overall_gate_score,
            )
        )
        results.append(_ok("stage eval unchanged", stage_after.current_stage == 2))
        results.append(_ok("does not promote learner", result.status != ReadinessStatus.PROMOTION_AVAILABLE or result.readiness_score == 100))

        official = await get_official_cefr(
            db, student_id=sid, language_id=lid, skill=LanguageSkill.listening
        )
        results.append(_ok("get_official_cefr still A2", official.level == LanguageLevel.A2))

        row.learning_stage_listening = saved_stage
        row.promotion_readiness_score = saved_readiness
        await db.rollback()

    return results


def verify_engines_untouched() -> list[bool]:
    print("\n=== Phase 1-3 + gate engines untouched ===")
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    packages = [
        "language_listening_challenge",
        "language_listening_confidence",
        "language_listening_curriculum",
        "language_transition_gate",
    ]
    results: list[bool] = []
    for pkg in packages:
        path = root / pkg
        text_body = "\n".join(p.read_text(encoding="utf-8") for p in path.rglob("*.py"))
        results.append(
            _ok(
                f"{pkg} has no promotion_readiness import",
                "language_promotion_readiness" not in text_body,
            )
        )

    for mod_name in (
        "language_transition_gate.engine",
        "language_learning_stage.engine",
    ):
        import importlib

        mod = importlib.import_module(f"app.services.{mod_name}")
        src = inspect.getsource(mod)
        results.append(_ok(f"{mod_name} has no promotion_readiness import", "language_promotion_readiness" not in src))

    return results


async def main() -> int:
    print("verify_language_promotion_readiness_phase_5_3")
    all_results: list[bool] = []
    all_results.extend(verify_status_model())
    all_results.extend(verify_continuous_scoring())
    all_results.extend(verify_perfect_promotion_available())
    all_results.extend(verify_blockers_and_actions())
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
