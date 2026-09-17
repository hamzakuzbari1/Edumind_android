"""Time planner load with auto_generate forced (<2 planned slots)."""
import asyncio
import logging
import time
import sys
from pathlib import Path

logging.disable(logging.CRITICAL)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text

from app.core.test_users import TEST_USER_PASSWORD, default_test_email
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.planner import PlannerScheduleSlot, ScheduleSlotStatus
from app.models.user import User
from app.services.planner_intelligence_service import compute_subject_analytics, get_enriched_planner_state


async def find_heavy_student_id():
    async with AsyncSessionLocal() as db:
        row = await db.execute(
            text(
                """
                SELECT sp.user_id, sp.grade, COUNT(DISTINCT sca.course_id) AS courses
                FROM student_profiles sp
                LEFT JOIN student_course_access sca ON sca.student_id = sp.user_id
                WHERE sp.grade IS NOT NULL
                GROUP BY sp.user_id, sp.grade
                ORDER BY courses DESC NULLS LAST
                LIMIT 5
                """
            )
        )
        return row.fetchall()


async def time_analytics(student_id: int):
    async with AsyncSessionLocal() as db:
        t0 = time.perf_counter()
        rows = await compute_subject_analytics(db, student_id)
        return (time.perf_counter() - t0) * 1000, len(rows)


async def time_enriched(student_id: int, auto_generate: bool):
    async with AsyncSessionLocal() as db:
        t0 = time.perf_counter()
        await get_enriched_planner_state(db, student_id, auto_generate=auto_generate)
        await db.rollback()
        return (time.perf_counter() - t0) * 1000


async def main():
    students = await find_heavy_student_id()
    print("Top students by course access:", students)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t", timeout=120) as c:
        email = default_test_email("auth_student")
        login = await c.post(
            "/api/auth/login",
            json={"email": email, "password": TEST_USER_PASSWORD},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Force auto_generate path for test student
        async with AsyncSessionLocal() as db:
            user = (
                await db.execute(select(User).where(User.email == email))
            ).scalar_one()
            await db.execute(
                delete(PlannerScheduleSlot).where(
                    PlannerScheduleSlot.student_id == user.id,
                    PlannerScheduleSlot.status == ScheduleSlotStatus.planned,
                )
            )
            await db.commit()
            student_id = user.id

        for label, path in [
            ("planner_after_clear_slots", "/api/student/planner"),
            ("planner_summary", "/api/student/planner/summary"),
        ]:
            t0 = time.perf_counter()
            r = await c.get(path, headers=headers)
            ms = (time.perf_counter() - t0) * 1000
            print(f"HTTP {label}: status={r.status_code} ms={ms:.1f} size_kb={len(r.content)/1024:.1f}")

        ms, n = await time_analytics(student_id)
        print(f"compute_subject_analytics only: ms={ms:.1f} subjects={n}")

        ms = await time_enriched(student_id, auto_generate=False)
        print(f"get_enriched_planner_state auto_generate=False: ms={ms:.1f}")

        # clear again for auto_generate=True service timing
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(PlannerScheduleSlot).where(
                    PlannerScheduleSlot.student_id == student_id,
                    PlannerScheduleSlot.status == ScheduleSlotStatus.planned,
                )
            )
            await db.commit()

        ms = await time_enriched(student_id, auto_generate=True)
        print(f"get_enriched_planner_state auto_generate=True: ms={ms:.1f}")


if __name__ == "__main__":
    asyncio.run(main())
