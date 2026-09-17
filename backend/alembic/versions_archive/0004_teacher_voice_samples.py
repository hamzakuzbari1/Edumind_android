"""Teacher voice samples for AI persona/TTS.

Revision ID: 0004_teacher_voice_samples
Revises: 0003_course_manual_quizzes

Idempotent: table may already exist from legacy schema_patch.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_teacher_voice_samples"
down_revision = "0003_course_manual_quizzes"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    if not _table_exists("teacher_voice_samples"):
        op.create_table(
            "teacher_voice_samples",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("teacher_profile_id", sa.Integer(), nullable=False),
            sa.Column("storage_path", sa.String(length=1024), nullable=False),
            sa.Column("duration_seconds", sa.Float(), server_default="0", nullable=False),
            sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("processing_status", sa.String(length=32), server_default="pending", nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("transcript", sa.Text(), nullable=True),
            sa.Column("persona_prompt", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["teacher_profile_id"], ["teacher_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_teacher_voice_samples_profile "
        "ON teacher_voice_samples(teacher_profile_id)"
    )


def downgrade() -> None:
    op.drop_table("teacher_voice_samples")
