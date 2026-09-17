"""Vocabulary revamp Phase 3 — mastery counter.

Adds consecutive_good_count to language_vocabulary_progress so is_difficult
can be cleared after 3 consecutive Good/Easy grades.

Revision ID: 0010_vocabulary_mastery_counter
Revises: 0009_vocabulary_ai_foundation
Create Date: 2026-07-16
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0010_vocabulary_mastery_counter"
down_revision = "0009_vocabulary_ai_foundation"
branch_labels = None
depends_on = None

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def upgrade() -> None:
    sql = (_SQL_DIR / "0010_vocabulary_mastery_counter.sql").read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        "ALTER TABLE public.language_vocabulary_progress "
        "DROP COLUMN IF EXISTS consecutive_good_count;"
    )
