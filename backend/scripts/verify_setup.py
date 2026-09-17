"""
Verify local PostgreSQL connectivity and migrations readiness.

Run from backend/:
  python scripts/verify_setup.py
  alembic upgrade head
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import check_database_connection, engine, init_db


async def main() -> int:
    settings = get_settings()
    print("=" * 60)
    print("EduSpark local setup verification")
    print("=" * 60)
    print(f"Host:     {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
    print(f"Database: {settings.POSTGRES_DB}")
    print(f"User:     {settings.POSTGRES_USER}")
    print(f"URL:      {settings.DATABASE_URL.replace(settings.POSTGRES_PASSWORD, '****')}")
    print()

    try:
        print("[1/3] Testing asyncpg connection…")
        await check_database_connection()
        print("      OK — connected")

        print("[2/3] Database init (connectivity + optional pgvector)…")
        await init_db(max_retries=1)
        print("      OK — run: alembic upgrade head")

        print("[3/3] Checking users table…")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT email, role FROM users ORDER BY id"))
            rows = result.fetchall()
        for row in rows:
            print(f"      • {row[0]} ({row[1]})")

        print()
        print("SUCCESS — start API with:")
        print("  python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
        print("  http://127.0.0.1:8000/docs")
        return 0

    except Exception as exc:
        print(f"\nFAILED: {exc}\n")
        if "password authentication failed" in str(exc).lower():
            print("Fix: update project .env with your real PostgreSQL credentials.")
            print("Example if you use the default superuser:")
            print("  POSTGRES_USER=postgres")
            print("  POSTGRES_PASSWORD=YOUR_POSTGRES_PASSWORD")
            print()
            print("Or create the eduspark role:")
            print("  psql -U postgres -f backend/scripts/setup_local_db.sql")
        elif "does not exist" in str(exc).lower() and "eduspark" in str(exc).lower():
            print("Fix: create role/database — psql -U postgres -f backend/scripts/setup_local_db.sql")
        elif "vector" in str(exc).lower() and "extension" in str(exc).lower():
            print("Set ENABLE_PGVECTOR=false in .env (default) to skip pgvector.")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
