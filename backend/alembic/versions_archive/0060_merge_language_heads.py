"""Merge current language and voice migration heads.

Revision ID: 0060_merge_language_heads
Revises: 0045_elevenlabs_voice_ids, 0059_vocabulary_catalog, 18cb3f6657ce
"""

revision = "0060_merge_language_heads"
down_revision = (
    "0045_elevenlabs_voice_ids",
    "0059_vocabulary_catalog",
    "18cb3f6657ce",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
