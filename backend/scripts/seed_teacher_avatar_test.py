"""Set a test avatar on the seeded test teacher for local verification."""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.test_users import default_test_email

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

IMAGE_PATH = "/uploads/teachers/test/avatar_test.jpg"


async def main() -> None:
    # Refuse to run against what looks like a production database (DEBUG=false).
    # This script writes directly to the DB with no dry-run mode, so a misconfigured
    # environment must fail loudly rather than seed test data into production.
    if not get_settings().DEBUG:
        raise RuntimeError(
            "Refusing to seed test avatar: DEBUG is not enabled. This looks like a "
            "production database. Set DEBUG=true in .env if this is really a dev/test DB."
        )
    test_email = default_test_email("auth_teacher")
    conn = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        database=os.getenv("POSTGRES_DB", "eduspark"),
    )
    user_id = await conn.fetchval("SELECT id FROM users WHERE email = $1", test_email)
    if not user_id:
        print(f"Test teacher not found ({test_email}). Run: python scripts/seed_test_users.py")
        await conn.close()
        return

    await conn.execute(
        "UPDATE teacher_profiles SET image_url = $1 WHERE user_id = $2",
        IMAGE_PATH.replace("test", str(user_id)),
        user_id,
    )
    row = await conn.fetchrow(
        "SELECT user_id, full_name, image_url FROM teacher_profiles WHERE user_id = $1",
        user_id,
    )
    print("Updated test teacher:", dict(row) if row else None)
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
