"""Canonical grammar unit attempt truncation metadata.

Revision ID: 0012_grammar_canonical_unit_attempt_truncation
Revises: 0011_grammar_canonical_lesson_unit_attempts
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012_grammar_canonical_unit_attempt_truncation"
down_revision = "0011_grammar_canonical_lesson_unit_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "grammar_canonical_lesson_revision_unit_attempts",
        sa.Column("truncated", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("grammar_canonical_lesson_revision_unit_attempts", "truncated")
