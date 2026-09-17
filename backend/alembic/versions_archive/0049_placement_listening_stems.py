"""Make placement listening a real listening test: move the spoken phrase out of the
visible stem into a hidden `audio_transcript` field so learners must actually listen.

Revision ID: 0049_placement_listening_stems
Revises: 0048_merge_routine_tts_heads
"""
import json
import logging
import re

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger("alembic.runtime.migration.0049")

revision = "0049_placement_listening_stems"
down_revision = "0048_merge_routine_tts_heads"
branch_labels = None
depends_on = None

_UESC = re.compile(r"\\u([0-9a-fA-F]{4})")
_LEAD = re.compile(r'\s*You hear:\s*["“”](.*?)["“”]\s*(.*)', re.IGNORECASE | re.DOTALL)
_DEFAULT_Q = "Listen to the audio and choose the best answer."


def _clean(s: str) -> str:
    s = _UESC.sub(lambda m: chr(int(m.group(1), 16)), s or "")
    return s.replace("�", "'").strip()


def _as_dict(value):
    if isinstance(value, dict):
        return dict(value)
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, prompt_json FROM language_placement_questions "
            "WHERE question_type = 'mcq_listening'"
        )
    ).fetchall()
    updated = 0
    skipped = 0
    for qid, prompt in rows:
        data = _as_dict(prompt)
        stem = _clean(data.get("stem", ""))
        if data.get("audio_transcript"):
            skipped += 1
            continue
        m = _LEAD.match(stem)
        if not m:
            skipped += 1
            logger.warning("0049: skipped mcq_listening id=%s — stem did not match expected format: %r", qid, stem)
            continue
        data["audio_transcript"] = m.group(1).strip()
        data["stem"] = (m.group(2).strip() or _DEFAULT_Q)
        conn.execute(
            sa.text("UPDATE language_placement_questions SET prompt_json = cast(:p as jsonb) WHERE id = :i"),
            {"p": json.dumps(data, ensure_ascii=False), "i": qid},
        )
        updated += 1
    logger.warning("0049 placement listening stems: updated=%d skipped=%d (of %d)", updated, skipped, len(rows))


def downgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, prompt_json FROM language_placement_questions "
            "WHERE question_type = 'mcq_listening'"
        )
    ).fetchall()
    for qid, prompt in rows:
        data = _as_dict(prompt)
        transcript = data.pop("audio_transcript", None)
        if not transcript:
            continue
        data["stem"] = f'You hear: "{transcript}" {data.get("stem", "")}'.strip()
        conn.execute(
            sa.text("UPDATE language_placement_questions SET prompt_json = cast(:p as jsonb) WHERE id = :i"),
            {"p": json.dumps(data, ensure_ascii=False), "i": qid},
        )
