"""Store ElevenLabs voice ids for teacher voice samples.

Revision ID: 0045_elevenlabs_voice_ids
Revises: 0052_lesson_insights_json
"""

import sqlalchemy as sa
from alembic import op

revision = "0045_elevenlabs_voice_ids"
down_revision = "0052_lesson_insights_json"
branch_labels = None
depends_on = None


def _column_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c LIMIT 1"
        ),
        {"t": table, "c": column},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, "teacher_voice_samples", "elevenlabs_voice_id"):
        op.add_column(
            "teacher_voice_samples",
            sa.Column("elevenlabs_voice_id", sa.String(length=128), nullable=True),
        )
    if not _column_exists(conn, "teacher_voice_samples", "elevenlabs_requires_verification"):
        op.add_column(
            "teacher_voice_samples",
            sa.Column(
                "elevenlabs_requires_verification",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "teacher_voice_samples", "elevenlabs_requires_verification"):
        op.drop_column("teacher_voice_samples", "elevenlabs_requires_verification")
    if _column_exists(conn, "teacher_voice_samples", "elevenlabs_voice_id"):
        op.drop_column("teacher_voice_samples", "elevenlabs_voice_id")
