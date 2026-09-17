"""Verified lesson completion — quiz score, completion type, parent visibility."""

from alembic import op
import sqlalchemy as sa

revision = "0028_verified_lesson_completion"
down_revision = "0027_lesson_completion_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "student_lesson_progress",
        sa.Column("quiz_score_percent", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "student_lesson_progress",
        sa.Column("completion_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "student_lesson_progress",
        sa.Column("completion_percentage", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("student_lesson_progress", "completion_percentage")
    op.drop_column("student_lesson_progress", "completion_type")
    op.drop_column("student_lesson_progress", "quiz_score_percent")
