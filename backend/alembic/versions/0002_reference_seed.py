"""EduSpark Syria — canonical reference/seed data.

Seeds the reference content the app ships with (RBAC roles + the English
language-learning curriculum: language, product, content items, placement
sections/questions, conversation scenarios) from
``alembic/sql/0002_reference_seed.sql``.

Kept separate from the schema baseline so a fresh clone gets a working Language
module out of the box. User data (accounts, courses, lessons, subjects) is NOT
seeded.
"""
from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0002_reference_seed"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def _run_sql_file(name: str) -> None:
    sql = (_SQL_DIR / name).read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql)


def upgrade() -> None:
    _run_sql_file("0002_reference_seed.sql")


def downgrade() -> None:
    # Delete in reverse FK dependency order.
    op.get_bind().exec_driver_sql(
        """
        DELETE FROM public.language_conversation_scenarios;
        DELETE FROM public.language_placement_questions;
        DELETE FROM public.language_placement_sections;
        DELETE FROM public.language_content_items;
        DELETE FROM public.language_products;
        DELETE FROM public.languages;
        DELETE FROM public.roles;
        """
    )
