"""Merge orphaned routine slot migration with language TTS cache head."""

from alembic import op

revision = "0048_merge_routine_tts_heads"
down_revision = ("0009_routine_slot_status", "0047_lesson_tts_cache")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
