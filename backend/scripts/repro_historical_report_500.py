"""Reproduce parent historical-report 500 — all linked pairs + HTTP."""

from __future__ import annotations

import asyncio
import sys
import traceback
from pathlib import Path

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.auth_session import AuthSession
from app.models.parent_link import ParentStudentLink
from app.models.user import User
from app.schemas.parent_historical_reports import ParentHistoricalReportOut
from app.services.parent_historical_reports_service import build_parent_historical_report

BASE = "http://127.0.0.1:8000"


async def test_service_all() -> list[tuple[User, User, Exception | None]]:
    failures: list[tuple[User, User, Exception | None]] = []
    async with AsyncSessionLocal() as db:
        links = list((await db.execute(select(ParentStudentLink))).scalars().all())
        print(f"\n=== Service layer ({len(links)} links) ===")
        for link in links:
            parent = await db.get(User, link.parent_id)
            student = await db.get(User, link.student_id)
            try:
                data = await build_parent_historical_report(db, student.id, period="this_week")
                ParentHistoricalReportOut(**data)
                print(f"OK parent={parent.id} student={student.id} has_data={data.get('has_data')}")
            except Exception as exc:
                print(f"FAIL parent={parent.id} student={student.id}: {exc}")
                traceback.print_exc()
                failures.append((parent, student, exc))
    return failures


async def test_http(parent: User, student: User) -> None:
    async with AsyncSessionLocal() as db:
        sess = await db.scalar(
            select(AuthSession)
            .where(AuthSession.user_id == parent.id, AuthSession.revoked_at.is_(None))
            .order_by(AuthSession.created_at.desc())
        )
    token = create_access_token({"sub": str(parent.id), "role": parent.role.value}, session_id=sess.id if sess else None)
    headers = {"Authorization": f"Bearer {token}"}
    print(f"\n=== HTTP parent={parent.id} student={student.id} ===")
    with httpx.Client(timeout=60) as client:
        for period in ("this_week", "last_week", "this_month", "last_month"):
            path = f"/api/parent/historical-report?period={period}&student_id={student.id}"
            r = client.get(f"{BASE}{path}", headers=headers)
            print(f"{period} -> {r.status_code}")
            if r.status_code >= 400:
                print(r.text[:8000])


async def main() -> int:
    failures = await test_service_all()
    async with AsyncSessionLocal() as db:
        links = list((await db.execute(select(ParentStudentLink))).scalars().all())
        for link in links:
            parent = await db.get(User, link.parent_id)
            student = await db.get(User, link.student_id)
            await test_http(parent, student)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
