"""Daily progress snapshots for analytics time-series. New table only (additive, reversible).

Revision ID: 0057_progress_snapshots
Revises: 0056_pronunciation_scores
"""

import sqlalchemy as sa
from alembic import op

revision = "0057_progress_snapshots"
down_revision = "0056_pronunciation_scores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "language_progress_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("overall_rank", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reading_rank", sa.Integer(), server_default="0", nullable=False),
        sa.Column("listening_rank", sa.Integer(), server_default="0", nullable=False),
        sa.Column("writing_rank", sa.Integer(), server_default="0", nullable=False),
        sa.Column("speaking_rank", sa.Integer(), server_default="0", nullable=False),
        sa.Column("xp_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("vocabulary_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pronunciation_avg", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "language_id", "snapshot_date", name="uq_language_progress_snapshot"),
    )
    op.create_index("ix_language_progress_snapshots_student_id", "language_progress_snapshots", ["student_id"])
    op.create_index("ix_language_progress_snapshots_language_id", "language_progress_snapshots", ["language_id"])
    op.create_index("ix_language_progress_snapshots_snapshot_date", "language_progress_snapshots", ["snapshot_date"])


def downgrade() -> None:
    op.drop_index("ix_language_progress_snapshots_snapshot_date", table_name="language_progress_snapshots")
    op.drop_index("ix_language_progress_snapshots_language_id", table_name="language_progress_snapshots")
    op.drop_index("ix_language_progress_snapshots_student_id", table_name="language_progress_snapshots")
    op.drop_table("language_progress_snapshots")
