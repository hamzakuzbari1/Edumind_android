"""Print recent auth audit events for a test user email."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.test_users import default_test_email, is_test_user_email, require_test_user_email
from app.db.session import AsyncSessionLocal
from app.models.user import User

EMAIL = sys.argv[1] if len(sys.argv) > 1 else default_test_email("password_reset")


async def main() -> None:
    email = EMAIL.strip().lower()
    if not is_test_user_email(email):
        require_test_user_email(email, action="audit read")

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            print(f"USER_NOT_FOUND — run: python scripts/seed_test_users.py")
            return
        rows = await db.execute(
            text(
                """
                SELECT action, old_values, new_values, created_at
                FROM audit_logs
                WHERE entity_type = 'user' AND entity_id = :uid
                ORDER BY created_at DESC
                LIMIT 15
                """
            ),
            {"uid": user.id},
        )
        print(f"user_id={user.id} email={user.email}")
        for row in rows:
            print(dict(row._mapping))


if __name__ == "__main__":
    asyncio.run(main())
