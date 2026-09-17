"""Shared fixtures for ASGI integration and real PostgreSQL concurrency tests."""

from __future__ import annotations

import os

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Keep local unit runs usable while making DB-marked tests mandatory in the official image."""
    if os.getenv("TEST_DATABASE_RESET_ALLOWED") == "1":
        return
    skip = pytest.mark.skip(reason="requires the official backend-test PostgreSQL environment")
    for item in items:
        if "postgresql" in item.keywords or "concurrency" in item.keywords:
            item.add_marker(skip)


def _dedicated_test_database_url() -> str:
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        pytest.fail("DATABASE_URL is required for PostgreSQL tests")

    url = make_url(raw_url)
    expected_name = os.getenv("TEST_DATABASE_NAME", "").strip()
    if url.get_backend_name() != "postgresql":
        pytest.fail("PostgreSQL tests cannot run against SQLite or another database")
    if not expected_name.endswith("_test") or url.database != expected_name:
        pytest.fail("PostgreSQL tests require the dedicated *_test database")
    return raw_url


@pytest.fixture(scope="session")
def postgres_database_url() -> str:
    """Return a guarded URL that can only point at the disposable test database."""
    return _dedicated_test_database_url()


@pytest_asyncio.fixture
async def postgres_engine(postgres_database_url: str) -> AsyncEngine:
    """Provide a real asyncpg engine; each concurrent actor should open its own session."""
    engine = create_async_engine(postgres_database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            database_name = (await connection.execute(text("SELECT current_database()"))).scalar_one()
            assert database_name.endswith("_test")
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def postgres_session(postgres_engine: AsyncEngine) -> AsyncSession:
    """Provide a rollback-first session for tests that do not commit inside application code."""
    factory = async_sessionmaker(postgres_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def postgres_session_factory(postgres_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create independent sessions for genuine row-lock/concurrency tests."""
    return async_sessionmaker(postgres_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def asgi_app():
    """Import the assembled application lazily after test environment variables are installed."""
    from app.main import app

    return app


@pytest_asyncio.fixture
async def api_client(asgi_app):
    """Call the real FastAPI middleware/router stack without opening a network socket."""
    transport = httpx.ASGITransport(app=asgi_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        yield client
