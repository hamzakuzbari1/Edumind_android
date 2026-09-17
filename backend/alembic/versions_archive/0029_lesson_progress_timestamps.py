"""Lesson progress timestamps for parent timeline visibility."""

from alembic import op
import sqlalchemy as sa

revision = "0029_lesson_progress_timestamps"
down_revision = "0028_verified_lesson_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "student_lesson_progress",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "student_lesson_progress",
        sa.Column("video_last_watched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_student_lesson_progress_started_at",
        "student_lesson_progress",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_student_lesson_progress_started_at", table_name="student_lesson_progress")
    op.drop_column("student_lesson_progress", "video_last_watched_at")
    op.drop_column("student_lesson_progress", "started_at")
