"""Quick asyncpg connection test. Usage: python scripts/test_connection.py"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings


async def main():
    import asyncpg

    s = get_settings()
    print(f"Trying {s.POSTGRES_USER}@{s.POSTGRES_HOST}:{s.POSTGRES_PORT}/{s.POSTGRES_DB}")
    try:
        conn = await asyncpg.connect(
            host=s.POSTGRES_HOST,
            port=s.POSTGRES_PORT,
            user=s.POSTGRES_USER,
            password=s.POSTGRES_PASSWORD,
            database=s.POSTGRES_DB,
            timeout=10,
        )
        ver = await conn.fetchval("SELECT version()")
        print("OK:", ver[:60], "...")
        await conn.close()
        return 0
    except Exception as e:
        print("FAILED:", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
