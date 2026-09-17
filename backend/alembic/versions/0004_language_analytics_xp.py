"""Add XP progression columns to language_analytics."""
from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0004_language_analytics_xp"
down_revision = "0003_student_listening_content"
branch_labels = None
depends_on = None

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def upgrade() -> None:
    sql = (_SQL_DIR / "0004_language_analytics_xp.sql").read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        "ALTER TABLE public.language_analytics "
        "DROP COLUMN IF EXISTS xp_keys_json, "
        "DROP COLUMN IF EXISTS xp_total, "
        "DROP COLUMN IF EXISTS level_xp;"
    )
