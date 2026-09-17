"""E2E: login teacher, POST avatar, verify DB + status + student dashboard."""

from __future__ import annotations

import asyncio
import io
import json
import os
import sys
from pathlib import Path

import asyncpg
import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.test_users import TEST_USER_PASSWORD, default_test_email, require_test_user_email

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE = "http://127.0.0.1:8000"
# Minimal valid JPEG
JPEG = bytes([0xFF, 0xD8, 0xFF, 0xD9])


async def db_image_url(user_id: int) -> str | None:
    conn = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        database=os.getenv("POSTGRES_DB", "eduspark"),
    )
    row = await conn.fetchrow(
        "SELECT image_url FROM teacher_profiles WHERE user_id = $1",
        user_id,
    )
    await conn.close()
    return row["image_url"] if row else None


def login_teacher(client: httpx.Client) -> tuple[str, int, str]:
    if len(sys.argv) >= 3:
        email = require_test_user_email(sys.argv[1], action="avatar persistence test")
        password = sys.argv[2]
        candidates = [(email, password)]
    else:
        candidates = [(default_test_email("auth_teacher"), TEST_USER_PASSWORD)]
    for email, password in candidates:
        r = client.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
        if r.status_code == 200:
            data = r.json()
            return data["access_token"], data["user"]["id"], email
        print(f"login failed {email}: {r.status_code} {r.text[:200]}")
    raise SystemExit("No teacher login")


def main() -> int:
    with httpx.Client(timeout=30) as client:
        token, user_id, email = login_teacher(client)
        headers = {"Authorization": f"Bearer {token}"}
        print(f"Teacher: {email} user_id={user_id}")

        before = asyncio.run(db_image_url(user_id))
        print(f"DB image_url BEFORE: {before!r}")

        r = client.post(
            f"{BASE}/api/teacher/setup/avatar",
            headers=headers,
            files={"file": ("avatar_test.jpg", JPEG, "image/jpeg")},
        )
        print(f"POST /teacher/setup/avatar status={r.status_code}")
        print("Response:", json.dumps(r.json() if r.status_code == 200 else r.text[:500], ensure_ascii=False, indent=2))

        if r.status_code != 200:
            return 1

        after = asyncio.run(db_image_url(user_id))
        print(f"DB image_url AFTER: {after!r}")

        status = client.get(f"{BASE}/api/teacher/setup/status", headers=headers)
        print("GET /status image_url:", status.json().get("image_url") if status.status_code == 200 else status.text)

        student_email = default_test_email("auth_student")
        sr = client.post(
            f"{BASE}/api/auth/login",
            json={"email": student_email, "password": TEST_USER_PASSWORD},
        )
        if sr.status_code == 200:
            sh = {"Authorization": f"Bearer {sr.json()['access_token']}"}
            dash = client.get(f"{BASE}/api/student/dashboard", headers=sh)
            if dash.status_code == 200:
                for c in dash.json().get("courses") or []:
                    if c.get("teacher_image_url"):
                        print(
                            "Dashboard course",
                            c["id"],
                            c["teacher_name"],
                            c["teacher_image_url"],
                        )

        ok = bool(after and after.startswith("/uploads/"))
        print("PASS" if ok else "FAIL: image_url not persisted")
        return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
