"""AI speaking conversation sessions and turn evaluations."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0036_speaking_conversation"
down_revision = "0035_routine_tables"
branch_labels = None
depends_on = None

language_level = postgresql.ENUM(
    "A1", "A2", "B1", "B2", "C1", "C2",
    name="language_level",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "language_speaking_conversation_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("effective_level_at_start", language_level, nullable=True),
        sa.Column("turn_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_id"], ["languages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_language_speaking_conversation_sessions_student",
        "language_speaking_conversation_sessions",
        ["student_id", "language_id", "status"],
    )

    op.create_table(
        "language_speaking_conversation_turns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("user_transcript", sa.Text(), server_default="", nullable=False),
        sa.Column("assistant_reply", sa.Text(), server_default="", nullable=False),
        sa.Column("user_media_object_id", sa.Integer(), nullable=True),
        sa.Column("reply_media_object_id", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("evaluation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("estimated_cefr", language_level, nullable=True),
        sa.Column("scoring_version", sa.String(32), server_default="conversation_v1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["language_speaking_conversation_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_media_object_id"], ["media_objects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reply_media_object_id"], ["media_objects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_language_speaking_conversation_turns_session",
        "language_speaking_conversation_turns",
        ["session_id", "turn_index"],
    )
    op.create_index(
        "ix_language_speaking_conversation_turns_student",
        "language_speaking_conversation_turns",
        ["student_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_language_speaking_conversation_turns_student", table_name="language_speaking_conversation_turns")
    op.drop_index("ix_language_speaking_conversation_turns_session", table_name="language_speaking_conversation_turns")
    op.drop_table("language_speaking_conversation_turns")
    op.drop_index(
        "ix_language_speaking_conversation_sessions_student",
        table_name="language_speaking_conversation_sessions",
    )
    op.drop_table("language_speaking_conversation_sessions")
