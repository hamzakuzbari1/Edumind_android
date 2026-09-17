"""Planner intelligence: study streaks."""

from alembic import op
import sqlalchemy as sa

revision = "0021_planner_intelligence"
down_revision = "0020_parent_teacher_messaging"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_study_streaks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("current_streak_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("longest_streak_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("task_streak_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_study_date", sa.Date(), nullable=True),
        sa.Column("last_task_date", sa.Date(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", name="uq_student_study_streaks_student"),
    )
    op.create_index("ix_student_study_streaks_student_id", "student_study_streaks", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_student_study_streaks_student_id", table_name="student_study_streaks")
    op.drop_table("student_study_streaks")
