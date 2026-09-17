"""Smoke-test teacher profile CV CRUD."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.auth_session import AuthSession
from app.models.catalog import TeacherProfile
from app.models.user import User, UserRole

BASE = "http://127.0.0.1:8000"


async def main() -> None:
    async with AsyncSessionLocal() as db:
        tp = await db.scalar(select(TeacherProfile).limit(1))
        teacher = await db.get(User, tp.user_id)
        sess = await db.scalar(
            select(AuthSession)
            .where(AuthSession.user_id == teacher.id, AuthSession.revoked_at.is_(None))
            .order_by(AuthSession.created_at.desc())
        )
    assert teacher.role == UserRole.teacher
    token = create_access_token(
        {"sub": str(teacher.id), "role": teacher.role.value},
        session_id=sess.id if sess else None,
    )
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=30) as client:
        r = client.post(
            f"{BASE}/api/teacher/setup/qualifications",
            headers=headers,
            json={"title": "بكالوريوس فيزياء", "institution": "جامعة دمشق", "year": 2015},
        )
        print("create qualification", r.status_code)
        qid = r.json()["id"] if r.status_code == 200 else None

        r2 = client.get(f"{BASE}/api/teacher/setup/cv", headers=headers)
        print("get cv", r2.status_code, "quals", len(r2.json().get("qualifications", [])))

        if qid:
            r3 = client.delete(f"{BASE}/api/teacher/setup/qualifications/{qid}", headers=headers)
            print("delete qualification", r3.status_code)


if __name__ == "__main__":
    asyncio.run(main())
