"""Verify forgot-password does NOT create tokens or send email for unknown addresses."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import func, select, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import AsyncSessionLocal
from app.models.email_token import EmailToken, EmailTokenPurpose
from app.models.user import User

BASE = "http://127.0.0.1:8000"


async def main() -> int:
    unknown = f"not-in-eduspark-{int(datetime.now(timezone.utc).timestamp())}@example.com"
    known = "test.password@eduspark-test.dev"

    for label, email, expect_delta in (
        ("UNKNOWN", unknown, 0),
        ("KNOWN_TEST_USER", known, 1),
    ):
        print(f"\n{'='*60}\n=== {label}: {email} ===")
        async with AsyncSessionLocal() as db:
            user_id = await db.scalar(select(User.id).where(User.email == email.lower()))
            tokens_before = await db.scalar(
                select(func.count())
                .select_from(EmailToken)
                .where(EmailToken.purpose == EmailTokenPurpose.password_reset)
            )
            print("user_exists:", user_id is not None, f"(id={user_id})" if user_id else "")
            print("password_reset_tokens_before:", tokens_before)

        r = httpx.post(f"{BASE}/api/auth/forgot-password", json={"email": email}, timeout=15)
        print("HTTP status:", r.status_code)
        print("HTTP body:", r.json())

        async with AsyncSessionLocal() as db:
            tokens_after = await db.scalar(
                select(func.count())
                .select_from(EmailToken)
                .where(EmailToken.purpose == EmailTokenPurpose.password_reset)
            )
            delta = tokens_after - tokens_before
            print("password_reset_tokens_after:", tokens_after)
            print("tokens_created_delta:", delta)
            if delta != expect_delta:
                print(f"FAIL expected delta {expect_delta}, got {delta}")
                return 1
            print("PASS")

    print("\nAll forgot-password checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
