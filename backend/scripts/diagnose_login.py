"""Diagnose login for a user email (read-only; HTTP probes test users only).

Usage:
    python scripts/diagnose_login.py
    python scripts/diagnose_login.py test.auth.student@eduspark-test.dev
    python scripts/diagnose_login.py user@example.com --password secret
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import verify_password
from app.core.test_users import TEST_USER_PASSWORD, default_test_email, is_test_user_email, require_test_user_email
from app.db.session import AsyncSessionLocal
from app.models.user import User

BASE = "http://127.0.0.1:8000"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Login diagnostics (never mutates non-test accounts via HTTP)")
    parser.add_argument("email", nargs="?", default=default_test_email("auth_student"))
    parser.add_argument("--password", default=TEST_USER_PASSWORD, help="Single password to check (DB + optional HTTP)")
    args = parser.parse_args()

    email = args.email.strip().lower()
    password = args.password

    print("=== DB ===")
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            print("USER_NOT_FOUND")
            return 1
        print("user_id", user.id)
        print("role", user.role.value)
        print("email_verified_at", user.email_verified_at)
        print("is_test_user", is_test_user_email(email))
        print("password_ok", verify_password(password, user.hashed_password))

    if is_test_user_email(email):
        print("\n=== HTTP login (test user) ===")
        try:
            r = httpx.post(
                f"{BASE}/api/auth/login",
                json={"email": email, "password": password},
                timeout=10,
            )
            print("status", r.status_code, r.json().get("detail", "OK") if r.status_code != 200 else "OK")
        except Exception as exc:
            print("HTTP ERROR", exc)
    else:
        print("\n=== HTTP login skipped (non-test account — use test users for HTTP probes) ===")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
