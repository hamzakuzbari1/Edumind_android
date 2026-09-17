"""Lesson completion engine — video, PDF, and quiz progress tracking."""

from alembic import op
import sqlalchemy as sa

revision = "0027_lesson_completion_engine"
down_revision = "0026_student_activity_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "student_lesson_progress",
        sa.Column("video_progress_percent", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "student_lesson_progress",
        sa.Column("pdf_progress_percent", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "student_lesson_progress",
        sa.Column("pdf_opened", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "student_lesson_progress",
        sa.Column("quiz_submitted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "student_lesson_progress",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.alter_column(
        "student_lesson_progress",
        "completed_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        "student_lesson_progress",
        "completed_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    op.drop_column("student_lesson_progress", "updated_at")
    op.drop_column("student_lesson_progress", "quiz_submitted")
    op.drop_column("student_lesson_progress", "pdf_opened")
    op.drop_column("student_lesson_progress", "pdf_progress_percent")
    op.drop_column("student_lesson_progress", "video_progress_percent")
