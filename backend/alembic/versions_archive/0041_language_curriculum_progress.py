"""Per-objective curriculum progress tracking.

Revision ID: 0041_language_curriculum_progress
Revises: 0040_student_learning_profile
"""
import sqlalchemy as sa
from alembic import op

revision = "0041_language_curriculum_progress"
down_revision = "0040_student_learning_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "language_curriculum_progress",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.Column("objective_id", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="new", nullable=False),
        sa.Column("practice_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_practiced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mastered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_id"], ["languages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "objective_id", name="uq_language_curriculum_progress"),
    )
    op.create_index("ix_language_curriculum_progress_student_id", "language_curriculum_progress", ["student_id"])
    op.create_index("ix_language_curriculum_progress_language_id", "language_curriculum_progress", ["language_id"])
    op.create_index("ix_language_curriculum_progress_objective_id", "language_curriculum_progress", ["objective_id"])


def downgrade() -> None:
    op.drop_table("language_curriculum_progress")
