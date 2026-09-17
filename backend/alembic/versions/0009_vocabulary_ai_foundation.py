"""Vocabulary revamp Phase 1 — AI generation foundation.

Adds is_difficult/fail_count to language_vocabulary_progress and a
per-student daily counter table for the 10-word/day AI generation cap.

Revision ID: 0009_vocabulary_ai_foundation
Revises: 0008_speaking_live_budget
Create Date: 2026-07-15
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0009_vocabulary_ai_foundation"
down_revision = "0008_speaking_live_budget"
branch_labels = None
depends_on = None

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def upgrade() -> None:
    sql = (_SQL_DIR / "0009_vocabulary_ai_foundation.sql").read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        "DROP TABLE IF EXISTS public.language_vocabulary_ai_daily_usage;"
        "ALTER TABLE public.language_vocabulary_progress "
        "DROP COLUMN IF EXISTS is_difficult, "
        "DROP COLUMN IF EXISTS fail_count;"
    )
