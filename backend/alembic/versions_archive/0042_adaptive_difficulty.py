"""Adaptive difficulty — per-skill level state (idempotent create).

Revision ID: 0042_adaptive_difficulty
Revises: 0041_language_curriculum_progress

Creates language_skill_level_state when absent (e.g. fresh Syria DB).
Skips when the table already exists (e.g. legacy mixed migration history).
recent_scores_json is added by 0043_add_recent_scores_json.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0042_adaptive_difficulty"
down_revision = "0041_language_curriculum_progress"
branch_labels = None
depends_on = None

language_skill = postgresql.ENUM(
    "reading", "listening", "writing", "speaking", name="language_skill", create_type=False
)
language_level = postgresql.ENUM(
    "A1", "A2", "B1", "B2", "C1", "C2", name="language_level", create_type=False
)


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "language_skill_level_state" in insp.get_table_names():
        return

    op.create_table(
        "language_skill_level_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.Column("skill", language_skill, nullable=False),
        sa.Column("current_level", language_level, nullable=False),
        sa.Column("consecutive_pass_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("consecutive_fail_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_level_change_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_id"], ["languages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "language_id", "skill", name="uq_language_skill_level_state"),
    )
    op.create_index("ix_language_skill_level_state_student_id", "language_skill_level_state", ["student_id"])


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "language_skill_level_state" not in insp.get_table_names():
        return
    op.drop_index("ix_language_skill_level_state_student_id", table_name="language_skill_level_state")
    op.drop_table("language_skill_level_state")
