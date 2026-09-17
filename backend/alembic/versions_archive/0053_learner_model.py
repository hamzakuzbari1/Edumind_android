"""Unified Learner Model — new tables only (knowledge components + per-student mastery).

Additive: creates two new tables, touches nothing existing.

Revision ID: 0053_learner_model
Revises: 0052_lesson_insights_json
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0053_learner_model"
down_revision = "0052_lesson_insights_json"
branch_labels = None
depends_on = None

# Reference the existing PG enum types (do NOT re-create them).
_SKILL = postgresql.ENUM(
    "reading", "listening", "writing", "speaking",
    name="language_skill", create_type=False,
)
_LEVEL = postgresql.ENUM(
    "A1", "A2", "B1", "B2", "C1", "C2",
    name="language_level", create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "language_knowledge_components",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("display_skill", _SKILL, nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("cefr_level", _LEVEL, nullable=False),
        sa.Column("prerequisites", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_language_knowledge_components_code", "language_knowledge_components", ["code"], unique=True)

    op.create_table(
        "language_component_mastery",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_id", sa.Integer(), sa.ForeignKey("language_knowledge_components.id", ondelete="CASCADE"), nullable=False),
        sa.Column("p_mastery", sa.Float(), server_default="0.1", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("evidence_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ease_factor", sa.Float(), server_default="2.5", nullable=False),
        sa.Column("interval_days", sa.Integer(), server_default="1", nullable=False),
        sa.Column("repetition_number", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_weight", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "language_id", "component_id", name="uq_language_component_mastery"),
    )
    op.create_index("ix_language_component_mastery_student_id", "language_component_mastery", ["student_id"])
    op.create_index("ix_language_component_mastery_language_id", "language_component_mastery", ["language_id"])
    op.create_index("ix_language_component_mastery_component_id", "language_component_mastery", ["component_id"])
    op.create_index("ix_language_component_mastery_next_review_at", "language_component_mastery", ["next_review_at"])


def downgrade() -> None:
    op.drop_table("language_component_mastery")
    op.drop_index("ix_language_knowledge_components_code", table_name="language_knowledge_components")
    op.drop_table("language_knowledge_components")
