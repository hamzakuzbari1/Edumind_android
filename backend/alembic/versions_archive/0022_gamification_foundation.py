"""Gamification foundation: XP and achievements."""

from alembic import op
import sqlalchemy as sa

revision = "0022_gamification_foundation"
down_revision = "0021_planner_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_xp",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("total_xp", sa.Integer(), server_default="0", nullable=False),
        sa.Column("level", sa.Integer(), server_default="1", nullable=False),
        sa.Column("awarded_keys_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", name="uq_student_xp_student"),
    )
    op.create_index("ix_student_xp_student_id", "student_xp", ["student_id"])

    op.create_table(
        "student_achievements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("achievement_key", sa.String(80), nullable=False),
        sa.Column("icon", sa.String(16), server_default="", nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "unlocked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "achievement_key", name="uq_student_achievement"),
    )
    op.create_index("ix_student_achievements_student_id", "student_achievements", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_student_achievements_student_id", table_name="student_achievements")
    op.drop_table("student_achievements")
    op.drop_index("ix_student_xp_student_id", table_name="student_xp")
    op.drop_table("student_xp")
