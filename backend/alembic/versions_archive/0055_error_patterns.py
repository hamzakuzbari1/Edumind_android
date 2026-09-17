"""Error Intelligence — recurring learner error patterns. New table only (additive, reversible).

Revision ID: 0055_error_patterns
Revises: 0054_generated_questions
"""

import sqlalchemy as sa
from alembic import op

revision = "0055_error_patterns"
down_revision = "0054_generated_questions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "language_error_patterns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("error_type", sa.String(20), nullable=False),
        sa.Column("pattern_key", sa.String(200), nullable=False),
        sa.Column("incorrect_form", sa.Text(), nullable=False),
        sa.Column("corrected_form", sa.Text(), server_default="", nullable=False),
        sa.Column("context_sentence", sa.Text(), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "language_id", "pattern_key", name="uq_language_error_pattern"),
    )
    op.create_index("ix_language_error_patterns_student_id", "language_error_patterns", ["student_id"])
    op.create_index("ix_language_error_patterns_language_id", "language_error_patterns", ["language_id"])
    op.create_index("ix_language_error_patterns_pattern_key", "language_error_patterns", ["pattern_key"])


def downgrade() -> None:
    op.drop_index("ix_language_error_patterns_pattern_key", table_name="language_error_patterns")
    op.drop_index("ix_language_error_patterns_language_id", table_name="language_error_patterns")
    op.drop_index("ix_language_error_patterns_student_id", table_name="language_error_patterns")
    op.drop_table("language_error_patterns")
