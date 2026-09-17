"""Vocabulary revamp Phase 7 — fixed, per-level word bank.

Renames the (never-populated) language_vocabulary_catalog table in place
into language_vocabulary_word_bank: translation -> translation_ar,
context_theme -> topic, cefr_level varchar -> language_level enum, plus new
example_sentence_ar / image_prompt / sort_order / updated_at columns. Drops
the unused language_vocabulary_catalog_seen table (superseded by
language_vocabulary_progress, which is already keyed by lemma).

The ~130 pre-existing language_content_items rows from the old live-LLM
generator are left as orphaned history (test-session data, not real user
data) — no backfill.

Revision ID: 0011_vocabulary_word_bank
Revises: 0010_vocabulary_mastery_counter
Create Date: 2026-07-21
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0011_vocabulary_word_bank"
down_revision = "0010_vocabulary_mastery_counter"
branch_labels = None
depends_on = None

_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def upgrade() -> None:
    sql = (_SQL_DIR / "0011_vocabulary_word_bank.sql").read_text(encoding="utf-8")
    op.get_bind().exec_driver_sql(sql)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        "CREATE TABLE public.language_vocabulary_catalog_seen ("
        "id SERIAL PRIMARY KEY, "
        "student_id integer NOT NULL, "
        "catalog_id integer NOT NULL, "
        "seen_at timestamptz NOT NULL DEFAULT now(), "
        "CONSTRAINT uq_language_vocabulary_catalog_seen_student_catalog UNIQUE (student_id, catalog_id));"
    )
    bind.exec_driver_sql(
        "ALTER TABLE public.language_vocabulary_word_bank "
        "DROP COLUMN example_sentence_ar, "
        "DROP COLUMN image_prompt, "
        "DROP COLUMN sort_order, "
        "DROP COLUMN updated_at;"
    )
    bind.exec_driver_sql(
        "ALTER TABLE public.language_vocabulary_word_bank "
        "ALTER COLUMN cefr_level TYPE varchar(4) USING cefr_level::varchar;"
    )
    bind.exec_driver_sql(
        "ALTER TABLE public.language_vocabulary_word_bank RENAME COLUMN topic TO context_theme;"
    )
    bind.exec_driver_sql(
        "ALTER TABLE public.language_vocabulary_word_bank RENAME COLUMN translation_ar TO translation;"
    )
    bind.exec_driver_sql(
        "ALTER INDEX public.ix_language_vocabulary_word_bank_topic RENAME TO ix_language_vocabulary_catalog_context_theme;"
    )
    bind.exec_driver_sql(
        "ALTER INDEX public.ix_language_vocabulary_word_bank_word RENAME TO ix_language_vocabulary_catalog_word;"
    )
    bind.exec_driver_sql(
        "ALTER INDEX public.ix_language_vocabulary_word_bank_cefr_level RENAME TO ix_language_vocabulary_catalog_cefr_level;"
    )
    bind.exec_driver_sql(
        "ALTER TABLE public.language_vocabulary_word_bank "
        "RENAME CONSTRAINT uq_language_vocabulary_word_bank_word_level TO uq_language_vocabulary_catalog_word_level;"
    )
    bind.exec_driver_sql(
        "ALTER TABLE public.language_vocabulary_word_bank "
        "RENAME CONSTRAINT language_vocabulary_word_bank_pkey TO language_vocabulary_catalog_pkey;"
    )
    bind.exec_driver_sql(
        "ALTER TABLE public.language_vocabulary_word_bank RENAME TO language_vocabulary_catalog;"
    )
