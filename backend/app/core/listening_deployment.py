"""Listening deployment schema validation (migration safety — no business logic)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

ERROR_CODE = "DATABASE_MIGRATION_REQUIRED"

# Listening canonical stack: progression (Phase 4.2) + reservations (Phase 2.2).
REQUIRED_TABLES: dict[str, str] = {
    "language_progression": "0005_language_progression",
    "language_progression_events": "0005_language_progression",
    "language_listening_reservations": "0006_language_listening_reservations",
}

REQUIRED_INDEXES: dict[str, str] = {
    "ix_language_progression_official_overall_cefr": "0005_language_progression",
    "ix_language_progression_events_student_id": "0005_language_progression",
    "ix_language_progression_events_language_id": "0005_language_progression",
    "ix_language_progression_events_created_at": "0005_language_progression",
    "ix_language_listening_reservations_student_language": "0006_language_listening_reservations",
    "ix_language_listening_reservations_content_item": "0006_language_listening_reservations",
    "uq_language_listening_reservations_active": "0006_language_listening_reservations",
}

LISTENING_HEAD_MIGRATION = "0006_language_listening_reservations"


@dataclass(frozen=True, slots=True)
class ListeningDeploymentStatus:
    deployment_ready: bool
    listening_progression_ready: bool
    reservation_table_present: bool
    current_alembic_revision: str | None
    latest_alembic_revision: str | None
    missing_tables: tuple[str, ...]
    missing_indexes: tuple[str, ...]
    required_migration: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "deployment_ready": self.deployment_ready,
            "listening_progression_ready": self.listening_progression_ready,
            "reservation_table_present": self.reservation_table_present,
            "current_alembic_revision": self.current_alembic_revision,
            "latest_alembic_revision": self.latest_alembic_revision,
            "missing_tables": list(self.missing_tables),
            "missing_indexes": list(self.missing_indexes),
            "required_migration": self.required_migration,
        }


class ListeningDeploymentNotReadyError(Exception):
    """Raised when listening endpoints require schema that is not migrated."""

    def __init__(self, status: ListeningDeploymentStatus) -> None:
        self.status = status
        missing_table = status.missing_tables[0] if status.missing_tables else None
        required_migration = (
            REQUIRED_TABLES.get(missing_table) if missing_table else status.required_migration
        ) or LISTENING_HEAD_MIGRATION
        self.payload: dict[str, Any] = {
            "error": ERROR_CODE,
            "message": "Listening deployment schema is not ready. Run Alembic migrations.",
            "missing_table": missing_table,
            "required_migration": required_migration,
            "current_alembic_revision": status.current_alembic_revision,
            "latest_alembic_revision": status.latest_alembic_revision,
            "missing_tables": list(status.missing_tables),
            "missing_indexes": list(status.missing_indexes),
        }
        super().__init__(self.payload["message"])


def _alembic_script_directory() -> ScriptDirectory:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    return ScriptDirectory.from_config(config)


def get_latest_alembic_revision() -> str | None:
    heads = _alembic_script_directory().get_heads()
    if not heads:
        return None
    if len(heads) == 1:
        return heads[0]
    return heads[0]


async def _table_exists(db: AsyncSession, table_name: str) -> bool:
    result = await db.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = :table_name
            )
            """
        ),
        {"table_name": table_name},
    )
    return bool(result.scalar())


async def _index_exists(db: AsyncSession, index_name: str) -> bool:
    result = await db.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE schemaname = 'public' AND indexname = :index_name
            )
            """
        ),
        {"index_name": index_name},
    )
    return bool(result.scalar())


async def get_current_alembic_revision(db: AsyncSession) -> str | None:
    exists = await _table_exists(db, "alembic_version")
    if not exists:
        return None
    result = await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
    row = result.scalar_one_or_none()
    return str(row) if row else None


async def inspect_listening_deployment(db: AsyncSession) -> ListeningDeploymentStatus:
    """Check tables, indexes, and Alembic revision for listening deployment readiness."""
    missing_tables: list[str] = []
    for table in REQUIRED_TABLES:
        if not await _table_exists(db, table):
            missing_tables.append(table)

    missing_indexes: list[str] = []
    for index_name in REQUIRED_INDEXES:
        if not await _index_exists(db, index_name):
            missing_indexes.append(index_name)

    progression_ready = "language_progression" not in missing_tables
    reservation_present = "language_listening_reservations" not in missing_tables
    current = await get_current_alembic_revision(db)
    latest = get_latest_alembic_revision()
    deployment_ready = not missing_tables and not missing_indexes

    required_migration: str | None = None
    if missing_tables:
        required_migration = REQUIRED_TABLES[missing_tables[0]]
    elif current and latest and current != latest:
        required_migration = latest

    return ListeningDeploymentStatus(
        deployment_ready=deployment_ready,
        listening_progression_ready=progression_ready,
        reservation_table_present=reservation_present,
        current_alembic_revision=current,
        latest_alembic_revision=latest,
        missing_tables=tuple(missing_tables),
        missing_indexes=tuple(missing_indexes),
        required_migration=required_migration,
    )


async def assert_listening_deployment_ready(db: AsyncSession) -> ListeningDeploymentStatus:
    status = await inspect_listening_deployment(db)
    if not status.deployment_ready:
        raise ListeningDeploymentNotReadyError(status)
    return status


async def log_listening_deployment_startup_warnings(db: AsyncSession) -> ListeningDeploymentStatus:
    """Log a clear warning at startup when critical listening schema is missing."""
    status = await inspect_listening_deployment(db)
    if status.deployment_ready:
        logger.info(
            "Listening deployment schema OK (revision=%s, progression=%s, reservations=%s)",
            status.current_alembic_revision,
            status.listening_progression_ready,
            status.reservation_table_present,
        )
        return status

    logger.warning(
        "LISTENING DEPLOYMENT NOT READY — run: alembic upgrade head | "
        "current_revision=%s latest_revision=%s missing_tables=%s missing_indexes=%s "
        "progression_ready=%s reservation_table_present=%s required_migration=%s",
        status.current_alembic_revision,
        status.latest_alembic_revision,
        list(status.missing_tables),
        list(status.missing_indexes),
        status.listening_progression_ready,
        status.reservation_table_present,
        status.required_migration or LISTENING_HEAD_MIGRATION,
    )
    return status
