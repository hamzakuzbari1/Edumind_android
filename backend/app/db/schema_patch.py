"""Deprecated incremental patches for pre-Alembic databases.

Production: set APPLY_LEGACY_SCHEMA_PATCHES=false and run `alembic upgrade head`.
New tables (quizzes, voice, audit, media, etc.) are created only via Alembic migrations.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

STUDENT_PROFILE_PATCHES: tuple[tuple[str, str], ...] = (
    ("grade", "INTEGER"),
    ("onboarding_step", "VARCHAR(32) DEFAULT 'grade'"),
    ("onboarding_completed_at", "TIMESTAMPTZ"),
    ("payment_completed_at", "TIMESTAMPTZ"),
)

LESSON_PATCHES: tuple[tuple[str, str], ...] = (
    ("description", "TEXT"),
    ("video_url", "VARCHAR(1024)"),
    ("homework_path", "VARCHAR(1024)"),
    ("content_type", "VARCHAR(32) DEFAULT 'video'"),
    ("sort_order", "INTEGER DEFAULT 0"),
    ("is_visible", "BOOLEAN DEFAULT TRUE"),
    ("course_id", "INTEGER"),
    ("insights_json", "JSONB"),
)

COURSE_PATCHES: tuple[tuple[str, str], ...] = (
    ("description", "TEXT"),
    ("is_published", "BOOLEAN DEFAULT TRUE"),
    ("thumbnail_url", "VARCHAR(1024)"),
    ("banner_url", "VARCHAR(1024)"),
)


async def apply_schema_patches(conn: AsyncConnection) -> None:
    dialect = conn.dialect.name
    if dialect != "postgresql":
        logger.info("Schema patches skipped (dialect=%s)", dialect)
        return

    for column, definition in STUDENT_PROFILE_PATCHES:
        await conn.execute(
            text(f"ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS {column} {definition}")
        )

    await conn.execute(
        text(
            "UPDATE student_profiles SET onboarding_step = 'grade' "
            "WHERE onboarding_step IS NULL"
        )
    )

    for column, definition in LESSON_PATCHES:
        await conn.execute(
            text(f"ALTER TABLE lessons ADD COLUMN IF NOT EXISTS {column} {definition}")
        )

    for column, definition in COURSE_PATCHES:
        await conn.execute(
            text(f"ALTER TABLE courses ADD COLUMN IF NOT EXISTS {column} {definition}")
        )

    logger.warning(
        "Legacy column patches applied — migrate fully with Alembic and disable "
        "APPLY_LEGACY_SCHEMA_PATCHES in production"
    )
