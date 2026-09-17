"""Offline vocabulary catalog + per-student 'seen' tracking, seeded from vocabulary_seed.json.

New tables only (additive, reversible). Powers the infinite, LLM-free vocabulary generator.

Revision ID: 0059_vocabulary_catalog
Revises: 0058_ai_usage
"""

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0059_vocabulary_catalog"
down_revision = "0058_ai_usage"
branch_labels = None
depends_on = None

_SEED = Path(__file__).parent.parent / "seeds" / "vocabulary_seed.json"


def upgrade() -> None:
    catalog = op.create_table(
        "language_vocabulary_catalog",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("word", sa.String(80), nullable=False),
        sa.Column("part_of_speech", sa.String(40), server_default="", nullable=False),
        sa.Column("translation", sa.String(200), server_default="", nullable=False),
        sa.Column("definition", sa.Text(), server_default="", nullable=False),
        sa.Column("context_theme", sa.String(60), server_default="", nullable=False),
        sa.Column("example_sentence", sa.Text(), server_default="", nullable=False),
        sa.Column("cefr_level", sa.String(4), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("word", "cefr_level", name="uq_language_vocabulary_catalog_word_level"),
    )
    op.create_index("ix_language_vocabulary_catalog_word", "language_vocabulary_catalog", ["word"])
    op.create_index("ix_language_vocabulary_catalog_context_theme", "language_vocabulary_catalog", ["context_theme"])
    op.create_index("ix_language_vocabulary_catalog_cefr_level", "language_vocabulary_catalog", ["cefr_level"])

    op.create_table(
        "language_vocabulary_catalog_seen",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("catalog_id", sa.Integer(), sa.ForeignKey("language_vocabulary_catalog.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "catalog_id", name="uq_language_vocabulary_catalog_seen"),
    )
    op.create_index("ix_language_vocabulary_catalog_seen_student_id", "language_vocabulary_catalog_seen", ["student_id"])
    op.create_index("ix_language_vocabulary_catalog_seen_catalog_id", "language_vocabulary_catalog_seen", ["catalog_id"])

    # Seed the catalog from the JSON dataset (idempotent on a fresh table).
    rows = []
    try:
        for r in json.loads(_SEED.read_text(encoding="utf-8")):
            word = str(r.get("word") or "").strip()
            if not word:
                continue
            rows.append({
                "word": word,
                "part_of_speech": str(r.get("part_of_speech") or "").strip()[:40],
                "translation": str(r.get("arabic_translation") or r.get("translation") or "").strip()[:200],
                "definition": str(r.get("definition") or "").strip(),
                "context_theme": str(r.get("context_theme") or "").strip()[:60],
                "example_sentence": str(r.get("example_sentence") or "").strip(),
                "cefr_level": str(r.get("cefr_level") or "").strip().upper()[:4],
            })
    except FileNotFoundError:
        rows = []
    if rows:
        op.bulk_insert(catalog, rows)


def downgrade() -> None:
    op.drop_index("ix_language_vocabulary_catalog_seen_catalog_id", table_name="language_vocabulary_catalog_seen")
    op.drop_index("ix_language_vocabulary_catalog_seen_student_id", table_name="language_vocabulary_catalog_seen")
    op.drop_table("language_vocabulary_catalog_seen")
    op.drop_index("ix_language_vocabulary_catalog_cefr_level", table_name="language_vocabulary_catalog")
    op.drop_index("ix_language_vocabulary_catalog_context_theme", table_name="language_vocabulary_catalog")
    op.drop_index("ix_language_vocabulary_catalog_word", table_name="language_vocabulary_catalog")
    op.drop_table("language_vocabulary_catalog")
