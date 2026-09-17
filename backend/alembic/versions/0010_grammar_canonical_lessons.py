"""Canonical grammar lesson persistence foundation.

Revision ID: 0010_grammar_canonical_lessons
Revises: 0009_grammar_integrity
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_grammar_canonical_lessons"
down_revision = "0009_grammar_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grammar_canonical_lessons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grammar_id", sa.String(length=128), nullable=False),
        sa.Column("cefr_level", sa.String(length=16), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("methodology_version", sa.String(length=96), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "grammar_id",
            "cefr_level",
            "locale",
            "methodology_version",
            name="uq_grammar_canonical_lessons_identity",
        ),
    )
    op.create_index("ix_grammar_canonical_lessons_grammar_id", "grammar_canonical_lessons", ["grammar_id"])
    op.create_index("ix_grammar_canonical_lessons_cefr_level", "grammar_canonical_lessons", ["cefr_level"])
    op.create_index("ix_grammar_canonical_lessons_locale", "grammar_canonical_lessons", ["locale"])
    op.create_index(
        "ix_grammar_canonical_lessons_methodology_version",
        "grammar_canonical_lessons",
        ["methodology_version"],
    )

    op.create_table(
        "grammar_canonical_lesson_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("student_content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("server_teaching_metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("catalog_version", sa.String(length=64), nullable=True),
        sa.Column("authoring_provider", sa.String(length=64), nullable=True),
        sa.Column("authoring_model", sa.String(length=128), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("diagnostics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_artifact_ref", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ("
            "'draft', 'generating', 'validating', 'reviewable', "
            "'published', 'failed', 'archived'"
            ")",
            name="ck_grammar_canonical_lesson_revisions_status",
        ),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lesson_id"], ["grammar_canonical_lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "lesson_id",
            "revision_number",
            name="uq_grammar_canonical_lesson_revisions_number",
        ),
    )
    op.create_index(
        "ix_grammar_canonical_lesson_revisions_lesson_id",
        "grammar_canonical_lesson_revisions",
        ["lesson_id"],
    )
    op.create_index(
        "ix_grammar_canonical_lesson_revisions_content_hash",
        "grammar_canonical_lesson_revisions",
        ["content_hash"],
    )
    op.create_index(
        "ix_grammar_canonical_lesson_revisions_approved_by_user_id",
        "grammar_canonical_lesson_revisions",
        ["approved_by_user_id"],
    )
    op.create_index(
        "ix_grammar_canonical_lesson_revisions_lesson_status",
        "grammar_canonical_lesson_revisions",
        ["lesson_id", "status"],
    )
    op.create_index(
        "uq_grammar_canonical_lesson_revisions_one_published",
        "grammar_canonical_lesson_revisions",
        ["lesson_id"],
        unique=True,
        postgresql_where=sa.text("status = 'published'"),
    )

    op.add_column(
        "grammar_activity_sessions",
        sa.Column("published_revision_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_grammar_activity_sessions_published_revision_id",
        "grammar_activity_sessions",
        ["published_revision_id"],
    )
    op.create_foreign_key(
        "fk_grammar_activity_sessions_published_revision_id",
        "grammar_activity_sessions",
        "grammar_canonical_lesson_revisions",
        ["published_revision_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_grammar_activity_sessions_published_revision_id",
        "grammar_activity_sessions",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_grammar_activity_sessions_published_revision_id",
        table_name="grammar_activity_sessions",
    )
    op.drop_column("grammar_activity_sessions", "published_revision_id")

    op.drop_index(
        "uq_grammar_canonical_lesson_revisions_one_published",
        table_name="grammar_canonical_lesson_revisions",
    )
    op.drop_index(
        "ix_grammar_canonical_lesson_revisions_lesson_status",
        table_name="grammar_canonical_lesson_revisions",
    )
    op.drop_index(
        "ix_grammar_canonical_lesson_revisions_approved_by_user_id",
        table_name="grammar_canonical_lesson_revisions",
    )
    op.drop_index(
        "ix_grammar_canonical_lesson_revisions_content_hash",
        table_name="grammar_canonical_lesson_revisions",
    )
    op.drop_index(
        "ix_grammar_canonical_lesson_revisions_lesson_id",
        table_name="grammar_canonical_lesson_revisions",
    )
    op.drop_table("grammar_canonical_lesson_revisions")

    op.drop_index("ix_grammar_canonical_lessons_methodology_version", table_name="grammar_canonical_lessons")
    op.drop_index("ix_grammar_canonical_lessons_locale", table_name="grammar_canonical_lessons")
    op.drop_index("ix_grammar_canonical_lessons_cefr_level", table_name="grammar_canonical_lessons")
    op.drop_index("ix_grammar_canonical_lessons_grammar_id", table_name="grammar_canonical_lessons")
    op.drop_table("grammar_canonical_lessons")
