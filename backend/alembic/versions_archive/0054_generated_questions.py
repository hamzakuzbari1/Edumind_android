"""AI-generated verified question bank (component- + CEFR-tagged). New table only.

Revision ID: 0054_generated_questions
Revises: 0053_learner_model
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0054_generated_questions"
down_revision = "0053_learner_model"
branch_labels = None
depends_on = None

_SKILL = postgresql.ENUM("reading", "listening", "writing", "speaking", name="language_skill", create_type=False)
_LEVEL = postgresql.ENUM("A1", "A2", "B1", "B2", "C1", "C2", name="language_level", create_type=False)


def upgrade() -> None:
    op.create_table(
        "language_generated_questions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_code", sa.String(64), nullable=False),
        sa.Column("display_skill", _SKILL, nullable=False),
        sa.Column("cefr_level", _LEVEL, nullable=False),
        sa.Column("question_type", sa.String(32), server_default="mcq", nullable=False),
        sa.Column("prompt_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(16), server_default="placement", nullable=False),
        sa.Column("verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("verification_note", sa.String(400), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_language_generated_questions_language_id", "language_generated_questions", ["language_id"])
    op.create_index("ix_language_generated_questions_component_code", "language_generated_questions", ["component_code"])


def downgrade() -> None:
    op.drop_table("language_generated_questions")
