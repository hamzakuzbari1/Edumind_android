"""Vocabulary revamp Phase 7 follow-up — enforce word-bank content-item uniqueness.

Closes a race condition in _get_or_create_content_item(): a plain check-then-insert
had no DB-level backing, so two concurrent requests for the same never-before-seen
(level, word) could each create their own content item instead of sharing one.
Adds a partial unique index scoped to source='word_bank' rows only — verified zero
duplicates exist there; legacy pre-word-bank rows (ai_generated/unset source) keep
their pre-existing duplicates untouched, per prior "leave as orphaned history" call.

Revision ID: 0012_word_bank_content_item_uniqueness
Revises: 0011_vocabulary_word_bank
Create Date: 2026-07-21
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0012_word_bank_content_item_uniqueness"
down_revision = "0011_vocabulary_word_bank"
branch_labels = None
depends_on = None

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def upgrade() -> None:
    sql = (_SQL_DIR / "0012_word_bank_content_item_uniqueness.sql").read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        "DROP INDEX IF EXISTS public.uq_language_content_items_word_bank_word_level;"
    )
