"""Lesson-scoped grammar tutor chat persistence.

Revision ID: 0013_grammar_lesson_chat
Revises: 0012_grammar_canonical_unit_attempt_truncation
Create Date: 2026-07-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_grammar_lesson_chat"
down_revision = "0012_grammar_canonical_unit_attempt_truncation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grammar_lesson_chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grammar_activity_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("mode", sa.String(length=24), server_default="preview", nullable=False),
        sa.Column("status", sa.String(length=24), server_default="open", nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("mode IN ('preview', 'student')", name="ck_grammar_lesson_chat_sessions_mode"),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_grammar_lesson_chat_sessions_status"),
        sa.ForeignKeyConstraint(["revision_id"], ["grammar_canonical_lesson_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["grammar_activity_session_id"], ["grammar_activity_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grammar_lesson_chat_sessions_revision_id", "grammar_lesson_chat_sessions", ["revision_id"])
    op.create_index(
        "ix_grammar_lesson_chat_sessions_revision_status",
        "grammar_lesson_chat_sessions",
        ["revision_id", "status"],
    )
    op.create_index("ix_grammar_lesson_chat_sessions_grammar_activity_session_id", "grammar_lesson_chat_sessions", ["grammar_activity_session_id"])
    op.create_index("ix_grammar_lesson_chat_sessions_user_id", "grammar_lesson_chat_sessions", ["user_id"])
    op.create_index(
        "ix_grammar_lesson_chat_sessions_user_updated",
        "grammar_lesson_chat_sessions",
        ["user_id", "updated_at"],
    )

    op.create_table(
        "grammar_lesson_chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chat_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("public_content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("private_provider_metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("stop_reason", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_grammar_lesson_chat_messages_role"),
        sa.ForeignKeyConstraint(["chat_session_id"], ["grammar_lesson_chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grammar_lesson_chat_messages_chat_session_id", "grammar_lesson_chat_messages", ["chat_session_id"])
    op.create_index(
        "ix_grammar_lesson_chat_messages_session_created",
        "grammar_lesson_chat_messages",
        ["chat_session_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_grammar_lesson_chat_messages_session_created", table_name="grammar_lesson_chat_messages")
    op.drop_index("ix_grammar_lesson_chat_messages_chat_session_id", table_name="grammar_lesson_chat_messages")
    op.drop_table("grammar_lesson_chat_messages")

    op.drop_index("ix_grammar_lesson_chat_sessions_user_updated", table_name="grammar_lesson_chat_sessions")
    op.drop_index("ix_grammar_lesson_chat_sessions_user_id", table_name="grammar_lesson_chat_sessions")
    op.drop_index("ix_grammar_lesson_chat_sessions_grammar_activity_session_id", table_name="grammar_lesson_chat_sessions")
    op.drop_index("ix_grammar_lesson_chat_sessions_revision_status", table_name="grammar_lesson_chat_sessions")
    op.drop_index("ix_grammar_lesson_chat_sessions_revision_id", table_name="grammar_lesson_chat_sessions")
    op.drop_table("grammar_lesson_chat_sessions")
