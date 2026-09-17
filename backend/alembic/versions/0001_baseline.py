"""EduSpark Syria — consolidated baseline schema.

Single authoritative baseline for the first public release. It creates the
complete database schema (all tables, enums, indexes and constraints) from the
production schema snapshot in ``alembic/sql/0001_baseline_schema.sql``.

This replaces the pre-release migration history (0002..0061 and merge
revisions), which is preserved under ``alembic/versions_archive/`` and in git
history. Running ``alembic upgrade head`` on an empty PostgreSQL database now
produces the full, working schema in one step.
"""
from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def _run_sql_file(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql)


def upgrade() -> None:
    # Alembic auto-creates alembic_version.version_num as VARCHAR(32); several
    # revision ids in this project exceed that (e.g. 0006_language_listening_reservations,
    # 37 chars), which fails the version-stamp UPDATE after a later migration's DDL
    # already ran. Widen it up front so every fresh install can reach head.
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)")
    _run_sql_file("0001_baseline_schema.sql")


def downgrade() -> None:
    # Full baseline: reset the public schema, then restore Alembic's bookkeeping
    # table so its post-downgrade version update succeeds.
    op.get_bind().exec_driver_sql(
        """
        DROP SCHEMA public CASCADE;
        CREATE SCHEMA public;
        CREATE TABLE alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        );
        INSERT INTO alembic_version (version_num) VALUES ('0001_baseline');
        """
    )
