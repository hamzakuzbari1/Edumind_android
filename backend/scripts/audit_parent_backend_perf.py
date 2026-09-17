"""Backend endpoint timing + SQL query count for parent portal APIs."""
from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.disable(logging.CRITICAL)

from sqlalchemy import event, select

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal, engine
from app.models.auth_session import AuthSession
from app.models.user import User  # noqa: F401

STUDENT_ID = 5
PARENT_ID = 23

ENDPOINTS = [
    ("GET", "/api/parent/students"),
    ("GET", f"/api/parent/dashboard?student_id={STUDENT_ID}"),
    ("GET", f"/api/parent/subjects-teachers?student_id={STUDENT_ID}"),
    ("GET", f"/api/parent/executive-summary?student_id={STUDENT_ID}"),
    ("GET", f"/api/parent/historical-report?period=this_week&student_id={STUDENT_ID}"),
    ("GET", f"/api/parent/notifications?limit=50&student_id={STUDENT_ID}"),
    ("GET", f"/api/parent/notification-settings?student_id={STUDENT_ID}"),
    ("GET", f"/api/parent/activity-tracking/analytics?week_offset=0&month_offset=0&session_limit=30&student_id={STUDENT_ID}"),
    ("GET", "/api/notifications/unread-count"),
    ("GET", "/api/notifications?unread_only=false&limit=30"),
    ("GET", "/api/auth/me"),
]


async def get_token() -> str:
    async with AsyncSessionLocal() as db:
        sess = await db.scalar(
            select(AuthSession)
            .where(AuthSession.user_id == PARENT_ID, AuthSession.revoked_at.is_(None))
            .order_by(AuthSession.created_at.desc())
        )
    return create_access_token({"sub": str(PARENT_ID), "role": "parent"}, session_id=sess.id if sess else None)


async def main() -> None:
    import httpx

    token = await get_token()
    headers = {"Authorization": f"Bearer {token}"}
    base = "http://127.0.0.1:8000"

    # Count SQL per request via sync engine listener (uvicorn uses same pool)
    query_counts: dict[str, int] = {}

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        key = getattr(context, "audit_key", None)
        if key:
            query_counts[key] = query_counts.get(key, 0) + 1

    event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)

    results = []
    async with httpx.AsyncClient(base_url=base, headers=headers, timeout=120.0) as client:
        for method, path in ENDPOINTS:
            key = path.split("?")[0]
            query_counts[key] = 0
            # attach audit key via hack: use path as label
            t0 = time.perf_counter()
            # Run via fresh connection context — count via manual service calls instead
            r = await client.request(method, path)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            results.append({
                "endpoint": path.replace(f"student_id={STUDENT_ID}", "student_id={{id}}"),
                "status": r.status_code,
                "durationMs": round(elapsed_ms, 1),
            })

    results.sort(key=lambda x: x["durationMs"], reverse=True)
    print("=== BACKEND DIRECT TIMING (port 8000) ===")
    for r in results:
        flag = ""
        if r["durationMs"] >= 2000:
            flag = " [>2s]"
        elif r["durationMs"] >= 1000:
            flag = " [>1s]"
        elif r["durationMs"] >= 500:
            flag = " [>500ms]"
        print(f"{r['durationMs']:7.1f}ms {r['status']} {r['endpoint']}{flag}")

    # Service-layer query counts
    print("\n=== SERVICE LAYER SQL COUNTS ===")
    await audit_service_queries()


async def audit_service_queries() -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.parent_attendance_analytics_service import build_parent_attendance_analytics
    from app.services.parent_courses_visibility_service import build_parent_subjects_teachers
    from app.services.parent_executive_summary_service import build_parent_executive_summary
    from app.services.parent_historical_reports_service import build_parent_historical_report
    from app.services.parent_monitoring_service import build_full_parent_dashboard

    counts: list[tuple[str, int, float]] = []

    async def run(label: str, fn):
        n = 0

        def count_sql(conn, cursor, statement, parameters, context, executemany):
            nonlocal n
            n += 1

        event.listen(AsyncSessionLocal.kw["bind"].sync_engine, "before_cursor_execute", count_sql)
        try:
            t0 = time.perf_counter()
            async with AsyncSessionLocal() as db:
                parent = await db.get(User, PARENT_ID)
                await fn(db, parent)
            ms = (time.perf_counter() - t0) * 1000
            counts.append((label, n, ms))
        finally:
            event.remove(AsyncSessionLocal.kw["bind"].sync_engine, "before_cursor_execute", count_sql)

    await run(
        "build_full_parent_dashboard",
        lambda db, p: build_full_parent_dashboard(db, p, STUDENT_ID),
    )
    await run(
        "build_parent_executive_summary",
        lambda db, p: build_parent_executive_summary(db, p, STUDENT_ID),
    )
    await run(
        "build_parent_historical_report",
        lambda db, p: build_parent_historical_report(db, p, STUDENT_ID, period="this_week"),
    )
    await run(
        "build_parent_subjects_teachers",
        lambda db, p: build_parent_subjects_teachers(db, p, STUDENT_ID),
    )
    await run(
        "build_parent_attendance_analytics",
        lambda db, p: build_parent_attendance_analytics(db, p, STUDENT_ID, week_offset=0, month_offset=0, session_limit=30),
    )

    counts.sort(key=lambda x: x[2], reverse=True)
    for label, n, ms in counts:
        print(f"  {ms:7.1f}ms  {n:4d} queries  {label}")


if __name__ == "__main__":
    asyncio.run(main())
