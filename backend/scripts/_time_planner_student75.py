"""Time planner for student with most course access."""
import asyncio
import logging
import time
import sys
from pathlib import Path

logging.disable(logging.CRITICAL)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.models.planner import PlannerScheduleSlot, ScheduleSlotStatus
from app.models.user import User
from app.services.planner_intelligence_service import compute_subject_analytics, get_enriched_planner_state


async def main():
    student_id = 75
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == student_id))).scalar_one_or_none()
        print("student", student_id, user.email if user else "missing")

    ms, n = await time_analytics(student_id)
    print(f"analytics: {ms:.1f}ms subjects={n}")

    ms, sched = await time_enriched(student_id, False)
    print(f"enriched no auto: {ms:.1f}ms schedule_slots={sched}")

    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(PlannerScheduleSlot).where(
                PlannerScheduleSlot.student_id == student_id,
                PlannerScheduleSlot.status == ScheduleSlotStatus.planned,
            )
        )
        await db.commit()

    ms, sched = await time_enriched(student_id, True)
    print(f"enriched auto_generate: {ms:.1f}ms schedule_slots={sched}")


async def time_analytics(student_id):
    async with AsyncSessionLocal() as db:
        t0 = time.perf_counter()
        rows = await compute_subject_analytics(db, student_id)
        return (time.perf_counter() - t0) * 1000, len(rows)


async def time_enriched(student_id, auto_generate):
    async with AsyncSessionLocal() as db:
        t0 = time.perf_counter()
        state = await get_enriched_planner_state(db, student_id, auto_generate=auto_generate)
        await db.rollback()
        sched = len(state.get("schedule") or [])
        return (time.perf_counter() - t0) * 1000, sched


if __name__ == "__main__":
    asyncio.run(main())
