"""Per-student personalized listening content ownership on language_content_items."""
from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0003_student_listening_content"
down_revision = "0002_reference_seed"
branch_labels = None
depends_on = None

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def _run_sql_file(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql)


def upgrade() -> None:
    _run_sql_file("0003_student_listening_content.sql")


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DROP INDEX IF EXISTS public.ix_language_content_items_student_listening;
        ALTER TABLE public.language_content_items
            DROP CONSTRAINT IF EXISTS fk_language_content_items_student_id;
        ALTER TABLE public.language_content_items
            DROP COLUMN IF EXISTS student_id;
        """
    )
