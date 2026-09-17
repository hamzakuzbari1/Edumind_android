from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.base import Base

# IMPORTANT: ensure all models are imported so metadata is complete for autogenerate.
from app import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_sync_database_url() -> str:
    """Alembic requires a synchronous engine — never use asyncpg here."""
    settings = get_settings()
    return (
        os.getenv("SYNC_DATABASE_URL")
        or os.getenv("DATABASE_URL_SYNC")
        or settings.sync_database_url
    )


def run_migrations_offline() -> None:
    url = _get_sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_sync_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Alembic defaults version_num to VARCHAR(32), but this repository has
        # historical revision IDs longer than 32 characters. Ensure the
        # bookkeeping table can store them before Alembic updates it.
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(128) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
            """
        )
        connection.exec_driver_sql(
            "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"
        )
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
