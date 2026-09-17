"""Parent notification settings and student activity alert types."""

from alembic import op
import sqlalchemy as sa

revision = "0030_parent_notifications"
down_revision = "0029_lesson_progress_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parent_notification_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("login_alerts", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("logout_alerts", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("lesson_alerts", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("quiz_alerts", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("low_score_alerts", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("inactivity_alerts", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("planner_alerts", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("inactivity_days", sa.Integer(), server_default="3", nullable=False),
        sa.Column("low_score_threshold", sa.Integer(), server_default="60", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "student_id", name="uq_parent_notification_settings"),
    )
    op.create_index(
        "ix_parent_notification_settings_parent_id",
        "parent_notification_settings",
        ["parent_id"],
    )
    op.create_index(
        "ix_parent_notification_settings_student_id",
        "parent_notification_settings",
        ["student_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_parent_notification_settings_student_id", table_name="parent_notification_settings")
    op.drop_index("ix_parent_notification_settings_parent_id", table_name="parent_notification_settings")
    op.drop_table("parent_notification_settings")
