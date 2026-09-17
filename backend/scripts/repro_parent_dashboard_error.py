"""Reproduce parent dashboard 500 — finds linked parent/student and calls dashboard."""

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
from app.models.parent_link import ParentStudentLink
from app.models.user import User, UserRole
from app.services.parent_monitoring_service import build_full_parent_dashboard

BASE = "http://127.0.0.1:8000"


async def _find_linked_pair():
    async with AsyncSessionLocal() as db:
        row = await db.scalar(
            select(ParentStudentLink).order_by(ParentStudentLink.created_at.desc())
        )
        if not row:
            return None, None
        parent = await db.get(User, row.parent_id)
        student = await db.get(User, row.student_id)
        return parent, student


async def test_service_layer(parent, student) -> None:
    print("\n=== Service layer: build_full_parent_dashboard ===")
    async with AsyncSessionLocal() as db:
        try:
            data = await build_full_parent_dashboard(db, parent, student_id=student.id)
            print("OK keys:", list(data.keys()))
            ai = data.get("academic_intelligence")
            print("academic_intelligence:", type(ai), getattr(ai, "model_dump", lambda: ai)() if ai else None)
        except Exception:
            print("FAILED:")
            traceback.print_exc()


async def test_http(parent, student) -> None:
    token = create_access_token({"sub": str(parent.id), "role": parent.role.value, "sid": 1})
    headers = {"Authorization": f"Bearer {token}"}
    endpoints = [
        f"/api/parent/dashboard?student_id={student.id}",
        f"/api/parent/academic-intelligence?student_id={student.id}",
        f"/api/parent/students",
    ]
    print("\n=== HTTP endpoints ===")
    with httpx.Client(timeout=30) as client:
        for path in endpoints:
            r = client.get(f"{BASE}{path}", headers=headers)
            print(f"{path} -> {r.status_code}")
            if r.status_code >= 400:
                print(r.text[:2000])


async def main() -> int:
    parent, student = await _find_linked_pair()
    if not parent or not student:
        print("No linked parent/student found")
        return 1
    print(f"parent id={parent.id} email={parent.email}")
    print(f"student id={student.id} email={student.email} grade profile pending check")
    await test_service_layer(parent, student)
    await test_http(parent, student)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
