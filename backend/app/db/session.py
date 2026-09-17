"""Async SQLAlchemy engine, sessions, and schema initialization."""

import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.schema_patch import apply_schema_patches

logger = logging.getLogger(__name__)
settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    connect_args={"timeout": settings.DB_CONNECT_TIMEOUT},
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def check_database_connection() -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def _try_enable_pgvector(conn) -> bool:
    """Optional: only when ENABLE_PGVECTOR=true and extension is installed."""
    if not settings.ENABLE_PGVECTOR:
        logger.info("pgvector disabled — using text-based chunk retrieval")
        return False
    try:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logger.info("pgvector extension enabled")
        return True
    except Exception as exc:
        logger.warning("pgvector not available (%s) — continuing without vectors", exc)
        return False


async def init_db(max_retries: int = 3, retry_delay: float = 1.5) -> None:
    """Production DB init.

    IMPORTANT:
    - No create_all — use Alembic for full schema (`alembic upgrade head`).
    - Legacy runtime patches are opt-in via APPLY_LEGACY_SCHEMA_PATCHES.
    - Verifies connectivity and optional pgvector extension only by default.
    """
    last_error: Exception | None = None
    target = settings.database_display

    for attempt in range(1, max_retries + 1):
        try:
            await check_database_connection()
            async with engine.begin() as conn:
                await _try_enable_pgvector(conn)
                if settings.APPLY_LEGACY_SCHEMA_PATCHES:
                    await apply_schema_patches(conn)
                else:
                    logger.info("Legacy schema patches disabled — use Alembic migrations")
            logger.info("Database ready: %s", target)
            return
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                logger.warning("DB init attempt %s/%s failed, retrying…", attempt, max_retries)
                await asyncio.sleep(retry_delay)

    hint = (
        f"Cannot connect to PostgreSQL at {target}.\n"
        "• Ensure PostgreSQL is running\n"
        "• Check POSTGRES_USER / POSTGRES_PASSWORD in .env\n"
    )
    if last_error and "password authentication failed" in str(last_error).lower():
        hint += "• Wrong username/password\n"
    raise RuntimeError(f"{hint}Details: {last_error}") from last_error
