"""Pronunciation scores — per-attempt prosody history. New table only (additive, reversible).

Revision ID: 0056_pronunciation_scores
Revises: 0055_error_patterns
"""

import sqlalchemy as sa
from alembic import op

revision = "0056_pronunciation_scores"
down_revision = "0055_error_patterns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "language_pronunciation_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("overall", sa.Integer(), server_default="0", nullable=False),
        sa.Column("clarity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fluency", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pace", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("intonation", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source", sa.String(20), server_default="conversation", nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_language_pronunciation_scores_student_id", "language_pronunciation_scores", ["student_id"])
    op.create_index("ix_language_pronunciation_scores_language_id", "language_pronunciation_scores", ["language_id"])
    op.create_index("ix_language_pronunciation_scores_created_at", "language_pronunciation_scores", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_language_pronunciation_scores_created_at", table_name="language_pronunciation_scores")
    op.drop_index("ix_language_pronunciation_scores_language_id", table_name="language_pronunciation_scores")
    op.drop_index("ix_language_pronunciation_scores_student_id", table_name="language_pronunciation_scores")
    op.drop_table("language_pronunciation_scores")
