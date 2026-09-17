"""Verify parent subjects-teachers API."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.auth_session import AuthSession
from app.models.user import User
from app.schemas.parent_courses_visibility import ParentSubjectsTeachersOut
from app.services.parent_courses_visibility_service import build_parent_subjects_teachers

BASE = "http://127.0.0.1:8000"
PARENT_ID = 23
STUDENT_ID = 5


async def main() -> None:
    async with AsyncSessionLocal() as db:
        parent = await db.get(User, PARENT_ID)
        data = await build_parent_subjects_teachers(db, parent, STUDENT_ID)
        ParentSubjectsTeachersOut(**data.model_dump())
        print("Service OK:", json.dumps(data.model_dump(), ensure_ascii=False, indent=2)[:2000])

        sess = await db.scalar(
            select(AuthSession)
            .where(AuthSession.user_id == PARENT_ID, AuthSession.revoked_at.is_(None))
            .order_by(AuthSession.created_at.desc())
        )
    token = create_access_token(
        {"sub": str(PARENT_ID), "role": "parent"},
        session_id=sess.id if sess else None,
    )
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=60) as client:
        r = client.get(f"{BASE}/api/parent/subjects-teachers?student_id={STUDENT_ID}", headers=headers)
        print(f"\nHTTP subjects-teachers -> {r.status_code}")
        if r.status_code == 200:
            body = r.json()
            print(f"enrolled={body.get('enrolled_count')} available={body.get('available_count')}")
            if body.get("enrolled"):
                c = body["enrolled"][0]
                cid = c["course_id"]
                r2 = client.get(
                    f"{BASE}/api/parent/courses/{cid}/teacher-profile?student_id={STUDENT_ID}",
                    headers=headers,
                )
                print(f"HTTP teacher-profile -> {r2.status_code}")
                if r2.status_code == 200:
                    print("teacher:", r2.json().get("full_name"))
        else:
            print(r.text[:500])


if __name__ == "__main__":
    asyncio.run(main())
