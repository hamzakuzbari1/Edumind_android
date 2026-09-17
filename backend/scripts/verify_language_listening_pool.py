"""Verify Phase 2.2 guaranteed listening pool refill."""

from __future__ import annotations

import asyncio
import time

from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageSkill
from app.services.language_listening_service import (
    MAX_REFILL_ATTEMPTS,
    TARGET_UNSEEN_LISTENING_POOL,
    _adaptive_level,
    _refill_personalized_pool,
    _unseen_personalized_count,
    listening_pool_deficit,
    next_listening,
    simulate_guaranteed_refill,
)
from app.services.language_subscription_service import get_default_language

STUDENT_ID = 59  # Test Student — use a different student to exercise empty pool


def verify_simulated_cases() -> bool:
    print(f"TARGET_UNSEEN_LISTENING_POOL = {TARGET_UNSEEN_LISTENING_POOL}")
    print(f"MAX_REFILL_ATTEMPTS = {MAX_REFILL_ATTEMPTS}")
    ok = True

    cases = [
        ("A: 5 valid in one batch", [5], 5, 1),
        ("B: 4 then 1", [4, 1], 5, 2),
        ("C: 3 then 1 then 1", [3, 1, 1], 5, 3),
        ("D: all invalid", [0, 0, 0], 0, 3),
        ("D2: partial then stall", [2, 0, 0], 2, 3),
    ]
    print("\nSimulated guaranteed refill cases:")
    for label, yields, expected_remaining, expected_attempts in cases:
        remaining, generated, attempts = simulate_guaranteed_refill(yields)
        status = (
            "OK"
            if remaining == expected_remaining and attempts == expected_attempts
            else "FAIL"
        )
        print(
            f"  {label}: yields={yields} -> pool={remaining} "
            f"generated={generated} attempts={attempts} (expected pool={expected_remaining}, "
            f"attempts={expected_attempts}) [{status}]"
        )
        if status == "FAIL":
            ok = False

    print("\nDeficit examples (unchanged):")
    for remaining, expected in [(5, 0), (4, 1), (2, 3), (0, 5)]:
        got = listening_pool_deficit(remaining)
        status = "OK" if got == expected else "FAIL"
        print(f"  Remaining={remaining} -> deficit {got} (expected {expected}) [{status}]")
        if got != expected:
            ok = False

    return ok


async def verify_runtime_guaranteed() -> bool:
    ok = True
    async with AsyncSessionLocal() as db:
        language = await get_default_language(db)
        level = await _adaptive_level(db, student_id=STUDENT_ID, language_id=language.id)
        before = await _unseen_personalized_count(
            db, student_id=STUDENT_ID, language_id=language.id, level=level
        )
        total_before = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(LanguageContentItem)
                    .where(
                        LanguageContentItem.student_id == STUDENT_ID,
                        LanguageContentItem.skill == LanguageSkill.listening,
                    )
                )
            ).scalar()
            or 0
        )
        print(f"\nRuntime student={STUDENT_ID} unseen_before={before} total_before={total_before}")

        t0 = time.perf_counter()
        generated = await _refill_personalized_pool(
            db, student_id=STUDENT_ID, language_id=language.id, level=level
        )
        elapsed = time.perf_counter() - t0

        after = await _unseen_personalized_count(
            db, student_id=STUDENT_ID, language_id=language.id, level=level
        )
        total_after = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(LanguageContentItem)
                    .where(
                        LanguageContentItem.student_id == STUDENT_ID,
                        LanguageContentItem.skill == LanguageSkill.listening,
                    )
                )
            ).scalar()
            or 0
        )
        print(
            f"  Refill: generated={generated} unseen_after={after} "
            f"target={TARGET_UNSEEN_LISTENING_POOL} elapsed={elapsed:.2f}s"
        )
        ok = after >= before and total_after >= total_before
        if before < TARGET_UNSEEN_LISTENING_POOL:
            ok = ok and after >= min(before + generated, TARGET_UNSEEN_LISTENING_POOL)

        # Full pool: second refill must not call Claude (no new rows)
        gen2 = await _refill_personalized_pool(
            db, student_id=STUDENT_ID, language_id=language.id, level=level
        )
        total_after2 = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(LanguageContentItem)
                    .where(
                        LanguageContentItem.student_id == STUDENT_ID,
                        LanguageContentItem.skill == LanguageSkill.listening,
                    )
                )
            ).scalar()
            or 0
        )
        unseen2 = await _unseen_personalized_count(
            db, student_id=STUDENT_ID, language_id=language.id, level=level
        )
        print(
            f"  Second refill: unseen={unseen2} generated={gen2} "
            f"no_new_rows={total_after2 == total_after}"
        )
        if unseen2 >= TARGET_UNSEEN_LISTENING_POOL:
            ok = ok and gen2 == 0 and total_after2 == total_after

        lesson = await next_listening(db, student_id=STUDENT_ID)
        print(f"  next_listening served: {lesson is not None}")
        ok = ok and lesson is not None

    return ok


async def main() -> None:
    sim_ok = verify_simulated_cases()
    runtime_ok = await verify_runtime_guaranteed()
    passed = sim_ok and runtime_ok
    print("\nPASS" if passed else "\nFAIL")


if __name__ == "__main__":
    asyncio.run(main())
