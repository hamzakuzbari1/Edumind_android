"""Canonical grammar lesson sectioned unit attempts.

Revision ID: 0011_grammar_canonical_lesson_unit_attempts
Revises: 0010_grammar_canonical_lessons
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_grammar_canonical_lesson_unit_attempts"
down_revision = "0010_grammar_canonical_lessons"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grammar_canonical_lesson_revision_unit_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_key", sa.String(length=32), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("public_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("private_metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("blueprint_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("stop_reason", sa.String(length=64), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("diagnostics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_artifact_ref", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "unit_key IN ('blueprint', 'concept', 'examples', 'rules', 'practice', 'production')",
            name="ck_grammar_canonical_lesson_unit_attempts_unit_key",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'generating', 'validating', 'accepted', 'failed', 'superseded')",
            name="ck_grammar_canonical_lesson_unit_attempts_status",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["grammar_canonical_lesson_revisions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "revision_id",
            "unit_key",
            "attempt_number",
            name="uq_grammar_canonical_lesson_unit_attempts_number",
        ),
    )
    op.create_index(
        "ix_grammar_canonical_lesson_unit_attempts_revision_id",
        "grammar_canonical_lesson_revision_unit_attempts",
        ["revision_id"],
    )
    op.create_index(
        "ix_grammar_canonical_lesson_unit_attempts_unit_key",
        "grammar_canonical_lesson_revision_unit_attempts",
        ["unit_key"],
    )
    op.create_index(
        "ix_grammar_canonical_lesson_unit_attempts_content_hash",
        "grammar_canonical_lesson_revision_unit_attempts",
        ["content_hash"],
    )
    op.create_index(
        "ix_grammar_canonical_lesson_unit_attempts_revision_unit_status",
        "grammar_canonical_lesson_revision_unit_attempts",
        ["revision_id", "unit_key", "status"],
    )
    op.create_index(
        "uq_grammar_canonical_lesson_unit_attempts_one_accepted",
        "grammar_canonical_lesson_revision_unit_attempts",
        ["revision_id", "unit_key"],
        unique=True,
        postgresql_where=sa.text("status = 'accepted'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_grammar_canonical_lesson_unit_attempts_one_accepted",
        table_name="grammar_canonical_lesson_revision_unit_attempts",
    )
    op.drop_index(
        "ix_grammar_canonical_lesson_unit_attempts_revision_unit_status",
        table_name="grammar_canonical_lesson_revision_unit_attempts",
    )
    op.drop_index(
        "ix_grammar_canonical_lesson_unit_attempts_content_hash",
        table_name="grammar_canonical_lesson_revision_unit_attempts",
    )
    op.drop_index(
        "ix_grammar_canonical_lesson_unit_attempts_unit_key",
        table_name="grammar_canonical_lesson_revision_unit_attempts",
    )
    op.drop_index(
        "ix_grammar_canonical_lesson_unit_attempts_revision_id",
        table_name="grammar_canonical_lesson_revision_unit_attempts",
    )
    op.drop_table("grammar_canonical_lesson_revision_unit_attempts")
