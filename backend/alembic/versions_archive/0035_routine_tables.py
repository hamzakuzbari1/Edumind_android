"""Daily routine tables — student profiles and weekly slots."""

from alembic import op
import sqlalchemy as sa

revision = "0035_routine_tables"
down_revision = "0034_voice_clone_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_routine_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("grade_level", sa.String(20), server_default="", nullable=False),
        sa.Column("school_start", sa.String(8), server_default="07:30", nullable=False),
        sa.Column("school_end", sa.String(8), server_default="13:00", nullable=False),
        sa.Column("wake_time", sa.String(8), server_default="06:30", nullable=False),
        sa.Column("sleep_time", sa.String(8), server_default="22:00", nullable=False),
        sa.Column("school_days_json", sa.Text(), server_default="[1,2,3,4,0]", nullable=False),
        sa.Column("activities_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("onboarding_complete", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("chat_history_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("chat_stage", sa.String(32), server_default="start", nullable=False),
        sa.Column("day_data_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("updated_at", sa.Text(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", name="uq_student_routine_profiles_student_id"),
    )
    op.create_index(
        "ix_student_routine_profiles_student_id",
        "student_routine_profiles",
        ["student_id"],
    )

    op.create_table(
        "routine_slots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.String(8), nullable=False),
        sa.Column("end_time", sa.String(8), nullable=False),
        sa.Column("activity_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(120), nullable=True),
        sa.Column("is_fixed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(16), server_default="planned", nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["student_routine_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_routine_slots_profile_id", "routine_slots", ["profile_id"])


def downgrade() -> None:
    op.drop_index("ix_routine_slots_profile_id", table_name="routine_slots")
    op.drop_table("routine_slots")
    op.drop_index("ix_student_routine_profiles_student_id", table_name="student_routine_profiles")
    op.drop_table("student_routine_profiles")
