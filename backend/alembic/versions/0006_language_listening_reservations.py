"""Add listening session reservations (Phase 2.2)."""
from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0006_language_listening_reservations"
down_revision = "0005_language_progression"
branch_labels = None
depends_on = None

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def upgrade() -> None:
    sql = (_SQL_DIR / "0006_language_listening_reservations.sql").read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS public.language_listening_reservations;")
