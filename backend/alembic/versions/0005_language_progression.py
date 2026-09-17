"""Add official language progression tables (Phase 4.2.1)."""
from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0005_language_progression"
down_revision = "0004_language_analytics_xp"
branch_labels = None
depends_on = None

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def upgrade() -> None:
    sql = (_SQL_DIR / "0005_language_progression.sql").read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS public.language_progression_events;")
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS public.language_progression;")
