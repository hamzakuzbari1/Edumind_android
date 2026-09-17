"""
Create eduspark PostgreSQL role and enable pgvector (uses admin/superuser from .env).

Set in project .env (one-time):
  POSTGRES_ADMIN_USER=postgres
  POSTGRES_ADMIN_PASSWORD=your_postgres_install_password

Then run from backend/:
  python scripts/bootstrap_db.py
  python scripts/verify_setup.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings


async def main() -> int:
    import asyncpg

    s = get_settings()
    admin_user = os.getenv("POSTGRES_ADMIN_USER", "postgres")
    admin_password = os.getenv("POSTGRES_ADMIN_PASSWORD", s.POSTGRES_PASSWORD)

    if not admin_password:
        print("Set POSTGRES_ADMIN_PASSWORD in .env to your postgres superuser password.")
        return 1

    print(f"Connecting as admin '{admin_user}' to database '{s.POSTGRES_DB}'…")
    try:
        conn = await asyncpg.connect(
            host=s.POSTGRES_HOST,
            port=s.POSTGRES_PORT,
            user=admin_user,
            password=admin_password,
            database=s.POSTGRES_DB,
            timeout=15,
        )
    except asyncpg.InvalidCatalogNameError:
        print(f"Database '{s.POSTGRES_DB}' not found. Create it in pgAdmin first.")
        return 1
    except Exception as exc:
        print(f"Admin connection failed: {exc}")
        print("Update POSTGRES_ADMIN_USER / POSTGRES_ADMIN_PASSWORD in .env")
        return 1

    app_user = "eduspark"
    app_pass = os.getenv("POSTGRES_APP_PASSWORD", "eduspark")

    exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", app_user)
    if exists:
        await conn.execute(f"ALTER USER {app_user} WITH PASSWORD $1", app_pass)
        print(f"Updated password for role '{app_user}'")
    else:
        await conn.execute(f"CREATE USER {app_user} WITH LOGIN PASSWORD $1", app_pass)
        print(f"Created role '{app_user}'")

    from app.core.config import get_settings

    if get_settings().ENABLE_PGVECTOR:
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            print("Extension 'vector' enabled")
        except Exception as exc:
            print(f"pgvector skipped: {exc}")
    else:
        print("pgvector disabled (ENABLE_PGVECTOR=false)")

    await conn.execute(f"GRANT ALL ON SCHEMA public TO {app_user}")
    await conn.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {app_user}")
    await conn.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {app_user}")
    await conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {app_user}")

    await conn.close()

    print()
    print("Update .env to use the app role:")
    print(f"  POSTGRES_USER={app_user}")
    print(f"  POSTGRES_PASSWORD={app_pass}")
    print()
    print("Then run: python scripts/verify_setup.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
