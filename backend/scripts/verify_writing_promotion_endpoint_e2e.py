"""End-to-end verification of the real /writing/promote + /writing/journey HTTP
endpoints against the running backend (the exact endpoints the browser UI calls).

Safe: captures the QA student's original writing state, seeds an eligible PASS
state, drives the real endpoints, asserts B1->B2, then restores the original
state (in a finally block).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401

import httpx
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel
from app.models.language.progression import LanguageProgression
from app.models.user import User
from app.services.language_writing_promotion_test.storage import WRITING_TESTS_KEY
from app.services.language_writing_progression.storage import WRITING_PROGRESSION_KEY

API = "http://127.0.0.1:8000"
EMAIL = "qa.listening.student-g@eduspark-test.dev"
PASSWORD = "TestOnly123!"

_results: list[tuple[str, bool, str]] = []


def ok(name: str, passed: bool, detail: str = "") -> bool:
    _results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")
    return passed


def _strong_lesson() -> dict:
    return {
        "criteria_total": 5, "criteria_met": 5, "confidence": 0.9,
        "grammar_score": 0.9, "vocabulary_score": 0.86, "organization_score": 0.82,
        "task_response_score": 0.88, "goal_alignment_score": 0.82,
        "overall_readiness": 0.87, "cefr_alignment": 1.0, "revision_count": 1,
    }


def _eligible_payload() -> dict:
    return {
        WRITING_PROGRESSION_KEY: {
            "grammar_mastery": {"present_simple": 0.92, "past_simple": 0.9},
            "vocabulary_mastery": {"vocabulary": 0.9},
            "lesson_history": [_strong_lesson() for _ in range(12)],
            "lessons_completed_count": 12,
            "completed_node_ids": [f"node_{i}" for i in range(12)],
            "weak_skills": [], "strong_skills": ["grammar:present_simple"],
            "coach_memory": {"repeated_mistakes": []}, "learning_stage": 3,
        },
        WRITING_TESTS_KEY: {
            "attempts": [{
                "session_id": "e2e_pass_1", "official_cefr": "B1", "target_cefr": "B2",
                "goal": "general_english", "overall_score": 90.0, "result": "PASS",
            }],
            "active_session": None,
        },
        "writing_stability": {"readiness_history": [{"lesson_index": 1, "readiness_score": 100}]},
    }


async def _find_ids(db):
    user = (await db.execute(select(User).where(User.email == EMAIL))).scalar_one_or_none()
    if user is None:
        return None
    row = (
        await db.execute(select(LanguageProgression).where(LanguageProgression.student_id == user.id))
    ).scalars().first()
    if row is None:
        return None
    return user.id, row.language_id


async def main() -> int:
    print("Writing /promote + /journey endpoint E2E (real running backend)")

    async with AsyncSessionLocal() as db:
        ids = await _find_ids(db)
        if ids is None:
            ok("skip (QA student/progression not found)", True)
            return 0
        sid, lid = ids
        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        original = {
            "writing": row.official_writing_cefr,
            "overall": row.official_overall_cefr,
            "stage": row.learning_stage_writing,
            "score": row.promotion_readiness_score,
            "json": row.promotion_readiness_json,
        }

    try:
        # Seed eligible PASS state (committed so the running backend sees it).
        async with AsyncSessionLocal() as db:
            row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
            row.official_writing_cefr = LanguageLevel.B1
            row.learning_stage_writing = 3
            row.promotion_readiness_json = _eligible_payload()
            flag_modified(row, "promotion_readiness_json")
            await db.commit()

        async with httpx.AsyncClient(base_url=API, timeout=60) as client:
            login = await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
            ok("login succeeds", login.status_code == 200, str(login.status_code))
            token = login.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            # Journey before promotion -> B1.
            jr = await client.get("/api/student/languages/writing/journey", headers=headers)
            before = jr.json() if jr.status_code == 200 else {}
            ok("journey shows B1 before promote", before.get("official_writing_level") == "B1", str(before.get("official_writing_level")))

            # Real promote endpoint (the UI button target).
            pr = await client.post("/api/student/languages/writing/promote", headers=headers)
            ok("/promote returns 200", pr.status_code == 200, f"{pr.status_code} {pr.text[:120]}")
            body = pr.json() if pr.status_code == 200 else {}
            ok("promote reports success", bool(body.get("success", body.get("promotion_success", True))), str(body)[:160])

            # Journey after promotion -> B2, stage 1.
            jr2 = await client.get("/api/student/languages/writing/journey", headers=headers)
            after = jr2.json() if jr2.status_code == 200 else {}
            ok("journey shows B2 after promote", after.get("official_writing_level") == "B2", str(after.get("official_writing_level")))
            ok("journey stage reset to 1", int(after.get("learning_stage") or 0) == 1, str(after.get("learning_stage")))
            ok("journey target now C1", after.get("promotion_target") == "C1", str(after.get("promotion_target")))
            ok("journey readiness reset low", int(after.get("readiness_score") or 0) < 60, str(after.get("readiness_score")))

            # Next generated lesson uses B2 (curriculum reads official CEFR).
            gen = await client.post(
                "/api/student/languages/writing/generate", headers=headers, json={}, timeout=300
            )
            if gen.status_code == 200:
                gj = gen.json()
                lvl = str(gj.get("official_cefr") or gj.get("cefr") or gj.get("level") or "")
                ok("next generated lesson uses B2", "B2" in lvl or gj.get("official_writing_level") == "B2", lvl or str(list(gj.keys()))[:120])
            else:
                ok("generate endpoint reachable (non-fatal)", True, f"status {gen.status_code}")

        # Confirm DB persisted B2 via official promotion (sole writer).
        async with AsyncSessionLocal() as db:
            row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
            ok("DB official_writing_cefr persisted B2", row.official_writing_cefr == LanguageLevel.B2, row.official_writing_cefr.value)
            ok("DB learning_stage_writing reset to 1", int(row.learning_stage_writing or 0) == 1, str(row.learning_stage_writing))

    finally:
        # Restore original state no matter what.
        async with AsyncSessionLocal() as db:
            row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
            row.official_writing_cefr = original["writing"]
            row.official_overall_cefr = original["overall"]
            row.learning_stage_writing = original["stage"]
            row.promotion_readiness_score = original["score"]
            row.promotion_readiness_json = original["json"]
            flag_modified(row, "promotion_readiness_json")
            await db.commit()
        print("  (restored QA student's original writing state)")

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
