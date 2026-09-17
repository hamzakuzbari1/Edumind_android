"""Spaced repetition (SM-2) fields on vocabulary progress.

Revision ID: 0046_vocab_spaced_repetition
Revises: 0045_conversation_scenarios
"""
import sqlalchemy as sa
from alembic import op

revision = "0046_vocab_spaced_repetition"
down_revision = "0045_conversation_scenarios"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if not _has_column("language_vocabulary_progress", "next_review_at"):
        op.add_column(
            "language_vocabulary_progress",
            sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_column("language_vocabulary_progress", "interval_days"):
        op.add_column(
            "language_vocabulary_progress",
            sa.Column("interval_days", sa.Integer(), server_default="1", nullable=False),
        )
    if not _has_column("language_vocabulary_progress", "ease_factor"):
        op.add_column(
            "language_vocabulary_progress",
            sa.Column("ease_factor", sa.Float(), server_default="2.5", nullable=False),
        )
    if not _has_column("language_vocabulary_progress", "repetition_number"):
        op.add_column(
            "language_vocabulary_progress",
            sa.Column("repetition_number", sa.Integer(), server_default="0", nullable=False),
        )


def downgrade() -> None:
    if _has_column("language_vocabulary_progress", "repetition_number"):
        op.drop_column("language_vocabulary_progress", "repetition_number")
    if _has_column("language_vocabulary_progress", "ease_factor"):
        op.drop_column("language_vocabulary_progress", "ease_factor")
    if _has_column("language_vocabulary_progress", "interval_days"):
        op.drop_column("language_vocabulary_progress", "interval_days")
    if _has_column("language_vocabulary_progress", "next_review_at"):
        op.drop_column("language_vocabulary_progress", "next_review_at")
