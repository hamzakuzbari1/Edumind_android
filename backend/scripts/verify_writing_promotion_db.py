"""Writing promotion + official CEFR integration verification (real DB, rolled back).

Covers WPA eligibility gating, goal-aware session targeting the next CEFR,
failed-WPA-does-not-promote, passed-WPA promotes B1->B2, stage reset, readiness
reset, history preservation, idempotency, and journey reflecting the new level.

Non-destructive: every scenario ends with db.rollback().
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import text
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel
from app.models.language.progression import LanguageProgression
from app.services.language_progression_service import upsert_official_levels
from app.services.language_writing.enums import WritingGoal
from app.services.language_writing_journey.builder import build_writing_journey_bundle
from app.services.language_writing.enums import OfficialWritingCEFR
from app.services.language_writing_evaluator.engine import evaluate_writing_draft_sync
from app.services.language_writing_official_promotion import apply_writing_official_promotion
from app.services.language_writing_progression.engine import run_writing_progression_after_complete
from app.services.language_writing_progression.storage import writing_state_from_payload
from app.services.language_writing_promotion_test.engine import _minimal_blueprint
from app.services.language_writing_promotion_test import (
    check_writing_promotion_test_eligibility,
    create_writing_promotion_test_session,
)
from app.services.language_writing_promotion_test.storage import WRITING_TESTS_KEY
from app.services.language_writing_progression.storage import WRITING_PROGRESSION_KEY

_results: list[tuple[str, bool, str]] = []


def ok(name: str, passed: bool, detail: str = "") -> bool:
    _results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")
    return passed


def _strong_lesson() -> dict:
    return {
        "criteria_total": 5,
        "criteria_met": 5,
        "confidence": 0.9,
        "grammar_score": 0.9,
        "vocabulary_score": 0.86,
        "organization_score": 0.82,
        "task_response_score": 0.88,
        "goal_alignment_score": 0.82,
        "overall_readiness": 0.87,
        "cefr_alignment": 1.0,
        "revision_count": 1,
    }


def _promotion_available_state() -> dict:
    lessons = [_strong_lesson() for _ in range(12)]
    return {
        WRITING_PROGRESSION_KEY: {
            "grammar_mastery": {"present_simple": 0.92, "past_simple": 0.9},
            "vocabulary_mastery": {"vocabulary": 0.9},
            "lesson_history": lessons,
            "lessons_completed_count": 12,
            "completed_node_ids": [f"node_{i}" for i in range(12)],
            "weak_skills": [],
            "strong_skills": ["grammar:present_simple"],
            "coach_memory": {"repeated_mistakes": []},
            "learning_stage": 3,
        }
    }


def _seed_attempt(session_id: str, result: str, *, official: str = "B1", target: str = "B2") -> dict:
    return {
        WRITING_TESTS_KEY: {
            "attempts": [
                {
                    "session_id": session_id,
                    "official_cefr": official,
                    "target_cefr": target,
                    "goal": "general_english",
                    "overall_score": 88.0 if result == "PASS" else 40.0,
                    "result": result,
                }
            ],
            "active_session": None,
        }
    }


async def _sample(db):
    return (await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))).first()


async def _set_b1(db, sid, lid):
    await upsert_official_levels(
        db, student_id=sid, language_id=lid,
        reading=LanguageLevel.A2, listening=LanguageLevel.A2,
        writing=LanguageLevel.B1, speaking=LanguageLevel.A2, overall=LanguageLevel.A2,
        source="verify_writing_promo", force=True,
    )


async def verify_eligibility_gating() -> None:
    print("\n=== WPA eligibility gating (cases 8/10/11) ===")
    async with AsyncSessionLocal() as db:
        s = await _sample(db)
        if s is None:
            ok("skip (no progression rows)", True)
            return
        sid, lid = s[0], s[1]
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        await _set_b1(db, sid, lid)

        # NOT ready state -> not eligible.
        row.promotion_readiness_json = {WRITING_PROGRESSION_KEY: {"lesson_history": [], "learning_stage": 1}}
        flag_modified(row, "promotion_readiness_json")
        await db.flush()
        eligible, reason, score, target = await check_writing_promotion_test_eligibility(
            db, student_id=sid, language_id=lid
        )
        ok("fresh student NOT WPA-eligible", not eligible, f"score={score}")

        # Strong sustained state -> eligible, target B2.
        row.promotion_readiness_json = _promotion_available_state()
        row.learning_stage_writing = 3
        flag_modified(row, "promotion_readiness_json")
        await db.flush()
        eligible, reason, score, target = await check_writing_promotion_test_eligibility(
            db, student_id=sid, language_id=lid
        )
        ok("strong sustained -> WPA eligible", eligible, f"score={score}")
        ok("WPA targets next CEFR (B2)", target == "B2", target)

        session = await create_writing_promotion_test_session(
            db, student_id=sid, language_id=lid, goal=WritingGoal.business
        )
        ok("WPA session created when eligible", bool(session.get("eligible")))
        sess = session.get("session") or {}
        ok("session targets B2", str(sess.get("target_cefr")) == "B2", str(sess.get("target_cefr")))
        ok("session is goal-aware (business)", str(sess.get("goal")) == "business", str(sess.get("goal")))
        ok("session has tasks", len(sess.get("tasks") or []) >= 1)

        await db.rollback()


async def verify_failed_wpa_no_promote() -> None:
    print("\n=== Failed WPA does not change official CEFR (case 12) ===")
    async with AsyncSessionLocal() as db:
        s = await _sample(db)
        if s is None:
            ok("skip", True)
            return
        sid, lid = s[0], s[1]
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        await _set_b1(db, sid, lid)
        row.promotion_readiness_json = _seed_attempt("wpa_fail_1", "FAIL")
        flag_modified(row, "promotion_readiness_json")
        await db.flush()

        applied = await apply_writing_official_promotion(db, student_id=sid, language_id=lid, session_id="wpa_fail_1")
        await db.refresh(row)
        ok("FAIL attempt is denied", not applied.success, applied.reason)
        ok("official writing CEFR stays B1", row.official_writing_cefr == LanguageLevel.B1, row.official_writing_cefr.value)
        await db.rollback()


async def verify_pass_promotes() -> None:
    print("\n=== Passed WPA promotes B1 -> B2 + reset (cases 13/15/16) ===")
    async with AsyncSessionLocal() as db:
        s = await _sample(db)
        if s is None:
            ok("skip", True)
            return
        sid, lid = s[0], s[1]
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        await _set_b1(db, sid, lid)
        row.learning_stage_writing = 3
        # Seed strong state + a PASS attempt (history preserved through reset).
        payload = _promotion_available_state()
        payload.update(_seed_attempt("wpa_pass_1", "PASS"))
        payload["writing_stability"] = {"readiness_history": [{"lesson_index": 1, "readiness_score": 100}]}
        row.promotion_readiness_json = payload
        flag_modified(row, "promotion_readiness_json")
        await db.flush()

        applied = await apply_writing_official_promotion(db, student_id=sid, language_id=lid, session_id="wpa_pass_1")
        await db.refresh(row)
        ok("PASS promotes", applied.success, applied.reason)
        ok("old CEFR B1", applied.old_cefr == "B1", applied.old_cefr)
        ok("new CEFR B2", applied.new_cefr == "B2", applied.new_cefr)
        ok("official_writing_cefr updated to B2", row.official_writing_cefr == LanguageLevel.B2, row.official_writing_cefr.value)
        ok("learning stage reset to 1", row.learning_stage_writing == 1, str(row.learning_stage_writing))
        ok("readiness score reset to 0", row.promotion_readiness_score == 0, str(row.promotion_readiness_score))
        p = row.promotion_readiness_json or {}
        ok("readiness status reset NOT_READY", (p.get("writing_readiness") or {}).get("status") == "NOT_READY")
        ok("stage state reset to 1", (p.get(WRITING_PROGRESSION_KEY) or {}).get("learning_stage") == 1)
        ok("stability history preserved", len((p.get("writing_stability") or {}).get("readiness_history") or []) >= 1)
        ok("WPA attempt history preserved", len((p.get(WRITING_TESTS_KEY) or {}).get("attempts") or []) >= 1)
        proms = p.get("writing_official_promotions") or {}
        ok("promotion event recorded", len(proms.get("events") or []) >= 1)

        # Idempotency.
        again = await apply_writing_official_promotion(db, student_id=sid, language_id=lid, session_id="wpa_pass_1")
        ok("re-apply is idempotent", again.success and "Already" in again.reason, again.reason)

        # Journey reflects B2 (case 16) + next lesson uses B2 (case 17).
        bundle = await build_writing_journey_bundle(db, student_id=sid, language_id=lid)
        data = bundle.model_dump() if hasattr(bundle, "model_dump") else dict(bundle)
        ok("journey shows official B2", data.get("official_writing_level") == "B2", str(data.get("official_writing_level")))
        ok("journey stage back to 1", int(data.get("learning_stage") or 0) == 1, str(data.get("learning_stage")))
        ok("journey readiness low after reset", int(data.get("readiness_score") or 0) < 60, str(data.get("readiness_score")))
        ok("journey promotion target now C1", data.get("promotion_target") == "C1", str(data.get("promotion_target")))

        await db.rollback()


async def verify_completion_writer_persists_signals() -> None:
    print("\n=== Completion writer persists rich signals (case 8: completion feedback) ===")
    async with AsyncSessionLocal() as db:
        s = await _sample(db)
        if s is None:
            ok("skip", True)
            return
        sid, lid = s[0], s[1]
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        await _set_b1(db, sid, lid)
        row.promotion_readiness_json = {WRITING_PROGRESSION_KEY: {"lesson_history": [], "learning_stage": 1}}
        flag_modified(row, "promotion_readiness_json")
        await db.flush()

        bp = _minimal_blueprint(
            task={"task_type": "essay", "genre": "paragraph", "min_words": 40, "max_words": 200},
            goal=WritingGoal.travel,
        )
        draft = (
            "When I travelled to the coast last summer, I stayed in a small hotel near the beach. "
            "The staff were friendly and the room was clean and quiet. Every morning I walked along "
            "the shore because the weather was warm and calm. I enjoyed the trip and I would happily "
            "return, since the town was peaceful and the food was delicious."
        )
        ev = await asyncio.to_thread(
            evaluate_writing_draft_sync, draft, draft_id="c1", revision_number=1, blueprint=bp
        )

        await run_writing_progression_after_complete(
            db, student_id=sid, language_id=lid, content_item_id=999999,
            goal=WritingGoal.travel, official_cefr=OfficialWritingCEFR.B1,
            chain_id="chain_x", node_id="node_x", evaluation=ev, revision_count=1,
        )
        await db.refresh(row)
        state = writing_state_from_payload(dict(row.promotion_readiness_json or {}))
        hist = state.get("lesson_history") or []
        ok("lesson recorded in history", len(hist) >= 1)
        entry = hist[-1] if hist else {}
        for field in ("grammar_score", "vocabulary_score", "organization_score", "task_response_score", "cefr_alignment", "overall_readiness"):
            ok(f"history entry has {field}", field in entry, str(entry.get(field)))
        wr = (row.promotion_readiness_json or {}).get("writing_readiness") or {}
        ok("readiness recomputed after completion", "readiness_score" in wr, str(wr.get("readiness_score")))
        await db.rollback()


async def main() -> int:
    print("Writing Promotion + Official CEFR — DB integration verification")
    await verify_eligibility_gating()
    await verify_failed_wpa_no_promote()
    await verify_pass_promotes()
    await verify_completion_writer_persists_signals()

    print("\n" + "=" * 50)
    failed = [n for n, passed, _ in _results if not passed]
    if failed:
        print(f"RESULT: FAIL — {len(failed)} check(s) failed:")
        for n in failed:
            print("  -", n)
        return 1
    print(f"RESULT: PASS — {len(_results)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
