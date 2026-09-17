"""Count SQL queries per parent service (N+1 detection)."""
from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.disable(logging.CRITICAL)

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.models.user import User  # noqa: F401
from app.services.parent_attendance_analytics_service import build_parent_attendance_analytics
from app.services.parent_courses_visibility_service import build_parent_subjects_teachers
from app.services.parent_executive_summary_service import build_parent_executive_summary
from app.services.parent_historical_reports_service import build_parent_historical_report
from app.services.parent_monitoring_service import build_full_parent_dashboard

PARENT_ID = 23
STUDENT_ID = 5

query_count = 0


def _before_execute(conn, cursor, statement, parameters, context, executemany):
    global query_count
    query_count += 1


event.listen(engine.sync_engine, "before_cursor_execute", _before_execute)


async def measure(label: str, fn) -> tuple[int, float]:
    global query_count
    query_count = 0
    t0 = time.perf_counter()
    async with AsyncSessionLocal() as db:
        parent = await db.get(User, PARENT_ID)
        await fn(db, parent)
    ms = (time.perf_counter() - t0) * 1000
    return query_count, ms


async def main() -> None:
    rows = []
    rows.append(await measure(
        "build_full_parent_dashboard",
        lambda db, p: build_full_parent_dashboard(db, p, student_id=STUDENT_ID),
    ))
    rows.append(await measure(
        "build_parent_executive_summary",
        lambda db, p: build_parent_executive_summary(db, STUDENT_ID, parent_id=PARENT_ID),
    ))
    rows.append(await measure(
        "build_parent_historical_report",
        lambda db, p: build_parent_historical_report(db, STUDENT_ID, period="this_week"),
    ))
    rows.append(await measure(
        "build_parent_subjects_teachers",
        lambda db, p: build_parent_subjects_teachers(db, p, STUDENT_ID),
    ))
    rows.append(await measure(
        "build_parent_attendance_analytics",
        lambda db, p: build_parent_attendance_analytics(
            db, STUDENT_ID, week_offset=0, month_offset=0, session_limit=30
        ),
    ))

    print("=== SQL QUERY COUNT PER SERVICE ===")
    for label, (n, ms) in zip(
        [
            "build_full_parent_dashboard",
            "build_parent_executive_summary",
            "build_parent_historical_report",
            "build_parent_subjects_teachers",
            "build_parent_attendance_analytics",
        ],
        rows,
    ):
        flag = " [N+1?]" if n > 30 else ""
        print(f"  {ms:7.1f}ms  {n:4d} queries  {label}{flag}")

    # Simulated full page load (all endpoints sequentially)
    total_q = sum(r[0] for r in rows)
    total_ms = sum(r[1] for r in rows)
    print(f"\n  If all 5 run on every page: ~{total_q} queries, ~{total_ms:.0f}ms serial")
    print(f"  Browser fires 11 HTTP calls in parallel → wall clock ~max(individual)")


if __name__ == "__main__":
    asyncio.run(main())
