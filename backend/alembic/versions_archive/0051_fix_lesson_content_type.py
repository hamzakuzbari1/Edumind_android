"""Repair legacy reading/listening lessons so they are reachable by the lesson UI.

Revision ID: 0051_fix_lesson_content_type
Revises: 0050_seed_language_content

Legacy rows may have content_type 'reading_lesson'/'listening_lesson' with body keys
text/situation instead of passage/instructions. This forward-only data fix aligns them
with the lesson list/detail queries. Idempotent when no legacy rows remain.
"""
from alembic import op

revision = "0051_fix_lesson_content_type"
down_revision = "0050_seed_language_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE language_content_items
        SET content_type = 'lesson',
            body_json = body_json || jsonb_build_object(
                'passage', body_json->>'text',
                'passage_ar', body_json->>'text_ar'
            )
        WHERE skill::text = 'reading' AND content_type = 'reading_lesson'
        """
    )
    op.execute(
        """
        UPDATE language_content_items
        SET content_type = 'lesson',
            body_json = body_json || jsonb_build_object('instructions', body_json->>'situation')
        WHERE skill::text = 'listening' AND content_type = 'listening_lesson'
        """
    )


def downgrade() -> None:
    op.execute(
        "UPDATE language_content_items SET content_type = 'reading_lesson' "
        "WHERE skill::text = 'reading' AND content_type = 'lesson' AND body_json ? 'passage'"
    )
    op.execute(
        "UPDATE language_content_items SET content_type = 'listening_lesson' "
        "WHERE skill::text = 'listening' AND content_type = 'lesson' AND body_json ? 'instructions'"
    )
