"""Reset only the explicitly configured disposable PostgreSQL test database."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def main() -> None:
    if os.getenv("TEST_DATABASE_RESET_ALLOWED") != "1":
        raise SystemExit("Refusing database reset: TEST_DATABASE_RESET_ALLOWED is not enabled")

    raw_url = os.getenv("DATABASE_URL_SYNC") or os.getenv("SYNC_DATABASE_URL")
    if not raw_url:
        raise SystemExit("Refusing database reset: no synchronous test DATABASE_URL is configured")

    url = make_url(raw_url)
    expected_name = os.getenv("TEST_DATABASE_NAME", "").strip()
    expected_host = os.getenv("TEST_DATABASE_HOST", "").strip()
    if url.get_backend_name() != "postgresql":
        raise SystemExit("Refusing database reset: the configured database is not PostgreSQL")
    if not expected_name.endswith("_test") or url.database != expected_name:
        raise SystemExit("Refusing database reset: database name is not the dedicated *_test database")
    if expected_host and url.host != expected_host:
        raise SystemExit("Refusing database reset: database host is not the dedicated test host")

    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
