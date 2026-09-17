"""Interactive AI English exam sessions.

Revision ID: 0061_language_exam_sessions
Revises: 0060_merge_language_heads
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0061_language_exam_sessions"
down_revision = "0060_merge_language_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "language_exam_sessions",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "language_id",
            sa.Integer(),
            sa.ForeignKey("languages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("current_step", sa.Integer(), server_default="1", nullable=False),
        sa.Column("max_steps", sa.Integer(), server_default="6", nullable=False),
        sa.Column("scenario_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("chat_history", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("exam_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="in_progress", nullable=False),
        sa.Column("is_completed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("assessment_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_language_exam_sessions_student_id",
        "language_exam_sessions",
        ["student_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_language_exam_sessions_student_id", table_name="language_exam_sessions")
    op.drop_table("language_exam_sessions")
