"""Phase C1 — attempt_count on progress tables + 30 starter lessons."""

import json

import sqlalchemy as sa
from alembic import op

revision = "0010_language_c1"
down_revision = "0009_language_phase2"
branch_labels = None
depends_on = None

LEVELS = ("A1", "A2", "B1")
LESSONS_PER_LEVEL = 5

READING_PASSAGES = {
    "A1": [
        "Tom is a student. He goes to school every day. He likes English and math. His teacher is kind.",
        "Sara has a cat. The cat is small and white. It sleeps on the sofa. Sara feeds it every morning.",
        "My name is Ali. I live in Damascus. I have two brothers. We play football after school.",
        "The shop is open from nine to five. You can buy bread, milk, and fruit. The prices are good.",
        "It is sunny today. The sky is blue. Birds sing in the trees. Children play in the park.",
    ],
    "A2": [
        "Last weekend, Maya visited her grandmother in the countryside. They walked in the garden and picked apples.",
        "The library opens at eight in the morning. Students can borrow books for two weeks. Late returns cost a small fee.",
        "Ahmed started a new job at a café. He serves coffee and talks with customers. He wants to improve his English.",
        "Our class is planning a trip to the museum. We will learn about history and art. Permission forms are due Friday.",
        "Rain fell all night, but the sun came out in the afternoon. People opened their windows and dried their laundry.",
    ],
    "B1": [
        "Climate change affects weather patterns around the world. Scientists study ice cores and satellite data to understand long-term trends.",
        "Remote work has changed how teams communicate. Video meetings replace some office conversations, but clear writing remains essential.",
        "The novel follows a young engineer who moves abroad for her first job. She learns to balance ambition with friendships.",
        "Urban planners debate how to reduce traffic while keeping city centers lively. Bike lanes and public transport are popular proposals.",
        "Healthy sleep habits improve memory and mood. Experts recommend a regular schedule and limiting screens before bedtime.",
    ],
}


def _mcq_questions(prefix: str, passage_hint: str) -> list[dict]:
    return [
        {
            "id": f"{prefix}_q1",
            "type": "mcq",
            "stem": "What is this text mainly about?",
            "choices": ["Daily life", "Space travel", "Ancient history", "Cooking"],
            "correct_index": 0,
        },
        {
            "id": f"{prefix}_q2",
            "type": "mcq",
            "stem": "Which detail appears in the passage?",
            "choices": ["A random fact", passage_hint[:40] + "…", "A phone number", "A recipe"],
            "correct_index": 1,
        },
        {
            "id": f"{prefix}_q3",
            "type": "mcq",
            "stem": "The tone of the text is best described as:",
            "choices": ["Informative", "Angry", "Sarcastic", "Confused"],
            "correct_index": 0,
        },
    ]


def _reading_body(level: str, index: int) -> dict:
    passage = READING_PASSAGES[level][index - 1]
    key = f"c1_reading_{level.lower()}_{index:02d}"
    words = passage.split()[:3]
    vocab = [w.strip(".,!?") for w in words if w.strip(".,!?")]
    return {
        "seed_key": key,
        "passage": passage,
        "passage_ar": "اقرأ النص ثم أجب عن الأسئلة.",
        "questions": _mcq_questions(key, passage),
        "pass_threshold_percent": 70,
        "vocabulary": vocab,
    }


def _listening_body(level: str, index: int) -> dict:
    key = f"c1_listening_{level.lower()}_{index:02d}"
    audio_url = None
    if level == "A1" and index == 1:
        audio_url = "/language-assets/en/lessons/listening/a1-01.mp3"
    else:
        audio_url = f"/language-assets/en/lessons/listening/{level.lower()}-{index:02d}.mp3"
    return {
        "seed_key": key,
        "instructions": "Listen carefully, then answer the questions.",
        "questions": _mcq_questions(key, f"Listening lesson {level} #{index}"),
        "pass_threshold_percent": 70,
        "audio_url": audio_url,
        "vocabulary": ["listen", "answer", "lesson"],
    }


def upgrade() -> None:
    op.add_column(
        "language_reading_progress",
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "language_listening_progress",
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )

    bind = op.get_bind()
    lang_id = bind.execute(sa.text("SELECT id FROM languages WHERE code = 'en' LIMIT 1")).scalar()
    if not lang_id:
        return

    for level in LEVELS:
        for i in range(1, LESSONS_PER_LEVEL + 1):
            seed_key = f"c1_reading_{level.lower()}_{i:02d}"
            exists = bind.execute(
                sa.text(
                    "SELECT 1 FROM language_content_items "
                    "WHERE body_json->>'seed_key' = :key LIMIT 1"
                ),
                {"key": seed_key},
            ).scalar()
            if exists:
                continue
            body = _reading_body(level, i)
            bind.execute(
                sa.text(
                    """
                    INSERT INTO language_content_items
                      (language_id, skill, level, content_type, title, body_json, sort_order, is_published)
                    VALUES
                      (:lang_id, 'reading', :level, 'lesson', :title, CAST(:body AS jsonb), :sort_order, true)
                    """
                ),
                {
                    "lang_id": lang_id,
                    "level": level,
                    "title": f"Reading {level} — Lesson {i}",
                    "body": json.dumps(body),
                    "sort_order": i,
                },
            )

    for level in LEVELS:
        for i in range(1, LESSONS_PER_LEVEL + 1):
            seed_key = f"c1_listening_{level.lower()}_{i:02d}"
            exists = bind.execute(
                sa.text(
                    "SELECT 1 FROM language_content_items "
                    "WHERE body_json->>'seed_key' = :key LIMIT 1"
                ),
                {"key": seed_key},
            ).scalar()
            if exists:
                continue
            body = _listening_body(level, i)
            bind.execute(
                sa.text(
                    """
                    INSERT INTO language_content_items
                      (language_id, skill, level, content_type, title, body_json, sort_order, is_published)
                    VALUES
                      (:lang_id, 'listening', :level, 'lesson', :title, CAST(:body AS jsonb), :sort_order, true)
                    """
                ),
                {
                    "lang_id": lang_id,
                    "level": level,
                    "title": f"Listening {level} — Lesson {i}",
                    "body": json.dumps(body),
                    "sort_order": i,
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM language_content_items WHERE body_json->>'seed_key' LIKE 'c1_%'"
        )
    )
    op.drop_column("language_listening_progress", "attempt_count")
    op.drop_column("language_reading_progress", "attempt_count")
