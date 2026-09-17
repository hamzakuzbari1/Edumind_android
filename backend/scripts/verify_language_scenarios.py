"""Verify Phase 7.7 conversation scenarios — seeds, categories, adaptive helpers.

Usage (from backend/):
    python scripts/verify_language_scenarios.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PASS = 0
FAIL = 0


def ok(label: str) -> None:
    global PASS
    PASS += 1
    print(f"OK  {label}")


def fail(label: str, detail: str = "") -> None:
    global FAIL
    FAIL += 1
    msg = f"FAIL {label}"
    if detail:
        msg += f": {detail}"
    print(msg)


def test_constants() -> None:
    from app.services.language_conversation_scenario_service import SCENARIO_CATEGORIES, _LEVEL_INSTRUCTIONS

    expected = {
        "airport",
        "hotel",
        "restaurant",
        "university",
        "job_interview",
        "doctor",
        "shopping",
        "daily_conversation",
    }
    if set(SCENARIO_CATEGORIES) == expected:
        ok("8 scenario categories defined")
    else:
        fail("scenario categories", str(SCENARIO_CATEGORIES))

    if "A1" in _LEVEL_INSTRUCTIONS and "B2" in _LEVEL_INSTRUCTIONS:
        ok("level instructions A1 and B2")
    else:
        fail("level instructions missing")


def test_scenario_out() -> None:
    from app.models.language.enums import LanguageLevel
    from app.models.language.scenario import LanguageConversationScenario
    from app.services.language_conversation_scenario_service import _scenario_out

    sc = LanguageConversationScenario(
        id=1,
        language_id=1,
        scenario_key="airport_checkin",
        category="airport",
        title_en="Airport",
        title_ar="مطار",
        level_min=LanguageLevel.A1,
        ai_role="officer",
        student_role="traveler",
        opening_line="Hello",
        target_skills_json=["speaking", "vocabulary"],
    )
    out = _scenario_out(sc, locked=False)
    if out.get("category") == "airport" and out.get("opening_message") == "Hello":
        ok("_scenario_out includes category and opening_message")
    else:
        fail("_scenario_out shape", str(out))


def test_pick_recommended() -> None:
    from app.models.language.enums import LanguageLevel
    from app.models.language.scenario import LanguageConversationScenario
    from app.services.language_conversation_scenario_service import _pick_recommended_next

    current = LanguageConversationScenario(
        id=1,
        language_id=1,
        scenario_key="airport_checkin",
        category="airport",
        title_en="Airport",
        title_ar="A",
        level_min=LanguageLevel.A1,
        ai_role="x",
        student_role="y",
        opening_line="Hi",
        is_active=True,
        sort_order=0,
    )
    nxt = LanguageConversationScenario(
        id=2,
        language_id=1,
        scenario_key="hotel_reception",
        category="hotel",
        title_en="Hotel",
        title_ar="B",
        level_min=LanguageLevel.A2,
        ai_role="x",
        student_role="y",
        opening_line="Hi",
        is_active=True,
        sort_order=1,
    )
    rec = _pick_recommended_next([current, nxt], current=current, student_rank=2, scores={"communication": 80})
    if rec and rec["id"] == 2:
        ok("_pick_recommended_next selects next scenario")
    else:
        fail("_pick_recommended_next", str(rec))


async def test_db_seeds() -> None:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.language.scenario import LanguageConversationScenario
    from app.services.language_subscription_service import get_default_language

    checks = [
        ("airport", "A1"),
        ("job_interview", "B1"),
        ("university", "B2"),
    ]

    async with AsyncSessionLocal() as db:
        try:
            language = await get_default_language(db)
        except Exception as e:
            fail("DB connection", str(e))
            return

        for category, level in checks:
            result = await db.execute(
                select(LanguageConversationScenario).where(
                    LanguageConversationScenario.language_id == language.id,
                    LanguageConversationScenario.category == category,
                    LanguageConversationScenario.is_active.is_(True),
                )
            )
            row = result.scalar_one_or_none()
            if not row:
                fail(f"seed {category}", "not found — run alembic upgrade head")
                continue
            if row.level_min.value != level:
                fail(f"seed {category}", f"expected {level}, got {row.level_min.value}")
            else:
                ok(f"seed {category} @ {level} ({row.title_en})")

            if not row.target_skills_json:
                fail(f"seed {category} target_skills", "empty")
            else:
                ok(f"seed {category} target_skills")


async def main() -> None:
    print("=== Phase 7.7 Conversation Scenarios Verification ===\n")
    test_constants()
    test_scenario_out()
    test_pick_recommended()
    await test_db_seeds()
    print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
    if FAIL:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
