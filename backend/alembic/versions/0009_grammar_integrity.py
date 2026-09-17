"""Wave D — grammar activity sessions + append-only evidence ledger.

Revision ID: 0009_grammar_integrity
Revises: 0008_speaking_live_budget
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_grammar_integrity"
down_revision = "0008_speaking_live_budget"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grammar_activity_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("grammar_id", sa.String(length=128), nullable=False),
        sa.Column("skill", sa.String(length=64), nullable=False),
        sa.Column("activity_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("lesson_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("content_item_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("stamp_token", sa.Text(), nullable=False),
        sa.Column("curriculum_version", sa.String(length=32), nullable=False, server_default="1.1.0"),
        sa.Column("server_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grammar_activity_sessions_student_id", "grammar_activity_sessions", ["student_id"])
    op.create_index("ix_grammar_activity_sessions_language_id", "grammar_activity_sessions", ["language_id"])
    op.create_index("ix_grammar_activity_sessions_grammar_id", "grammar_activity_sessions", ["grammar_id"])
    op.create_index(
        "ix_grammar_activity_sessions_content_item_id",
        "grammar_activity_sessions",
        ["content_item_id"],
    )
    op.create_index(
        "ix_grammar_activity_sessions_student_status",
        "grammar_activity_sessions",
        ["student_id", "status"],
    )

    op.create_table(
        "grammar_evidence_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_id", sa.String(length=191), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("grammar_id", sa.String(length=128), nullable=False),
        sa.Column("activity_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lesson_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("activity_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("skill", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("curriculum_version", sa.String(length=32), nullable=False, server_default="1.1.0"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["activity_session_id"],
            ["grammar_activity_sessions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id",
            "observation_id",
            name="uq_grammar_evidence_ledger_student_obs",
        ),
    )
    op.create_index("ix_grammar_evidence_ledger_student_id", "grammar_evidence_ledger", ["student_id"])
    op.create_index("ix_grammar_evidence_ledger_grammar_id", "grammar_evidence_ledger", ["grammar_id"])
    op.create_index(
        "ix_grammar_evidence_ledger_activity_session_id",
        "grammar_evidence_ledger",
        ["activity_session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_grammar_evidence_ledger_activity_session_id", table_name="grammar_evidence_ledger")
    op.drop_index("ix_grammar_evidence_ledger_grammar_id", table_name="grammar_evidence_ledger")
    op.drop_index("ix_grammar_evidence_ledger_student_id", table_name="grammar_evidence_ledger")
    op.drop_table("grammar_evidence_ledger")
    op.drop_index("ix_grammar_activity_sessions_student_status", table_name="grammar_activity_sessions")
    op.drop_index("ix_grammar_activity_sessions_content_item_id", table_name="grammar_activity_sessions")
    op.drop_index("ix_grammar_activity_sessions_grammar_id", table_name="grammar_activity_sessions")
    op.drop_index("ix_grammar_activity_sessions_language_id", table_name="grammar_activity_sessions")
    op.drop_index("ix_grammar_activity_sessions_student_id", table_name="grammar_activity_sessions")
    op.drop_table("grammar_activity_sessions")
