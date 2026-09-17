"""Cache generated lesson audio (teacher clone / gTTS / generic XTTS).

Revision ID: 0047_lesson_tts_cache
Revises: 0046_vocab_spaced_repetition
"""
import sqlalchemy as sa
from alembic import op

revision = "0047_lesson_tts_cache"
down_revision = "0046_vocab_spaced_repetition"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return name in insp.get_table_names()


def upgrade() -> None:
    if _table_exists("language_lesson_audio_cache"):
        return
    op.create_table(
        "language_lesson_audio_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_item_id", sa.Integer(), nullable=False),
        sa.Column("voice_source", sa.String(length=32), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("audio_storage_key", sa.String(length=1024), nullable=False),
        sa.Column("public_url", sa.String(length=2048), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["content_item_id"], ["language_content_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_item_id", "voice_source", "teacher_id", name="uq_language_lesson_audio_cache"),
    )
    op.create_index(
        "ix_language_lesson_audio_cache_content_item_id",
        "language_lesson_audio_cache",
        ["content_item_id"],
    )


def downgrade() -> None:
    if not _table_exists("language_lesson_audio_cache"):
        return
    op.drop_index("ix_language_lesson_audio_cache_content_item_id", table_name="language_lesson_audio_cache")
    op.drop_table("language_lesson_audio_cache")
