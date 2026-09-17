"""Merge vocabulary fixed bank with current language migration head.

Revision ID: 0015_merge_vocabulary_fixed_bank
Revises: 0014_merge_reading_v2_and_grammar_chat, 0012_word_bank_content_item_uniqueness
Create Date: 2026-07-25
"""

from __future__ import annotations

revision = "0015_merge_vocabulary_fixed_bank"
down_revision = (
    "0014_merge_reading_v2_and_grammar_chat",
    "0012_word_bank_content_item_uniqueness",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
