"""Reading Practice V2 backend foundation.

Revision ID: 0004_reading_v2_foundation
Revises: 0003_placement_qbank
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_reading_v2_foundation"
down_revision = "0003_placement_qbank"
branch_labels = None
depends_on = None


language_level = postgresql.ENUM("A1", "A2", "B1", "B2", "C1", "C2", name="language_level", create_type=False)


def upgrade() -> None:
    op.create_table(
        "language_reading_v2_student_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.Column("current_cefr", language_level, nullable=False),
        sa.Column("current_stage", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("unlocked_rank", sa.Integer(), nullable=False),
        sa.Column("readiness_target_level", language_level, nullable=True),
        sa.Column("recent_mastery_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["language_id"], ["languages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "language_id", name="uq_language_reading_v2_student_state"),
    )
    op.create_index(
        "ix_language_reading_v2_student_state_language_id",
        "language_reading_v2_student_state",
        ["language_id"],
    )
    op.create_index(
        "ix_language_reading_v2_student_state_student_id",
        "language_reading_v2_student_state",
        ["student_id"],
    )

    op.create_table(
        "language_reading_v2_stage_progress",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.Column("cefr_level", language_level, nullable=False),
        sa.Column("internal_stage", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempts_completed", sa.Integer(), nullable=False),
        sa.Column("mastery_score", sa.Float(), nullable=False),
        sa.Column("subskill_mastery_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("question_type_mastery_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recent_attempt_ids_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("mastered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["language_id"], ["languages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id",
            "language_id",
            "cefr_level",
            "internal_stage",
            name="uq_language_reading_v2_stage_progress",
        ),
    )
    op.create_index(
        "ix_language_reading_v2_stage_progress_cefr_level",
        "language_reading_v2_stage_progress",
        ["cefr_level"],
    )
    op.create_index(
        "ix_language_reading_v2_stage_progress_internal_stage",
        "language_reading_v2_stage_progress",
        ["internal_stage"],
    )
    op.create_index(
        "ix_language_reading_v2_stage_progress_language_id",
        "language_reading_v2_stage_progress",
        ["language_id"],
    )
    op.create_index(
        "ix_language_reading_v2_stage_progress_student_id",
        "language_reading_v2_stage_progress",
        ["student_id"],
    )

    op.create_table(
        "language_reading_v2_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.Column("cefr_level", language_level, nullable=False),
        sa.Column("internal_stage", sa.String(length=24), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("target_next_cefr", language_level, nullable=True),
        sa.Column("generation_blueprint_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_activity_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation_result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_used", sa.String(length=80), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("validator_version", sa.String(length=80), nullable=False),
        sa.Column("score_percent", sa.Float(), nullable=True),
        sa.Column("question_results_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["language_id"], ["languages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_language_reading_v2_attempts_cefr_level", "language_reading_v2_attempts", ["cefr_level"])
    op.create_index("ix_language_reading_v2_attempts_internal_stage", "language_reading_v2_attempts", ["internal_stage"])
    op.create_index("ix_language_reading_v2_attempts_language_id", "language_reading_v2_attempts", ["language_id"])
    op.create_index("ix_language_reading_v2_attempts_mode", "language_reading_v2_attempts", ["mode"])
    op.create_index("ix_language_reading_v2_attempts_status", "language_reading_v2_attempts", ["status"])
    op.create_index("ix_language_reading_v2_attempts_student_id", "language_reading_v2_attempts", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_language_reading_v2_attempts_student_id", table_name="language_reading_v2_attempts")
    op.drop_index("ix_language_reading_v2_attempts_status", table_name="language_reading_v2_attempts")
    op.drop_index("ix_language_reading_v2_attempts_mode", table_name="language_reading_v2_attempts")
    op.drop_index("ix_language_reading_v2_attempts_language_id", table_name="language_reading_v2_attempts")
    op.drop_index("ix_language_reading_v2_attempts_internal_stage", table_name="language_reading_v2_attempts")
    op.drop_index("ix_language_reading_v2_attempts_cefr_level", table_name="language_reading_v2_attempts")
    op.drop_table("language_reading_v2_attempts")
    op.drop_index("ix_language_reading_v2_stage_progress_student_id", table_name="language_reading_v2_stage_progress")
    op.drop_index("ix_language_reading_v2_stage_progress_language_id", table_name="language_reading_v2_stage_progress")
    op.drop_index("ix_language_reading_v2_stage_progress_internal_stage", table_name="language_reading_v2_stage_progress")
    op.drop_index("ix_language_reading_v2_stage_progress_cefr_level", table_name="language_reading_v2_stage_progress")
    op.drop_table("language_reading_v2_stage_progress")
    op.drop_index("ix_language_reading_v2_student_state_student_id", table_name="language_reading_v2_student_state")
    op.drop_index("ix_language_reading_v2_student_state_language_id", table_name="language_reading_v2_student_state")
    op.drop_table("language_reading_v2_student_state")
