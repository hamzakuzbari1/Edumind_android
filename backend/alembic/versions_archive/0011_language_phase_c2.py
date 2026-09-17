"""Phase C2 — vocabulary status, writing/speaking progress extensions + seed content."""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_language_c2"
down_revision = "0010_language_c1"
branch_labels = None
depends_on = None

language_vocabulary_status = postgresql.ENUM(
    "new", "learning", "known", name="language_vocabulary_status", create_type=False
)

LEVELS = ("A1", "A2", "B1")
VOCAB_PER_LEVEL = 20
PROMPTS_PER_LEVEL = 5

VOCAB_BANK = {
    "A1": [
        ("hello", "مرحباً", "Hello, my name is Tom."),
        ("goodbye", "مع السلامة", "Goodbye, see you tomorrow."),
        ("please", "من فضلك", "Please sit down."),
        ("thank you", "شكراً", "Thank you for your help."),
        ("yes", "نعم", "Yes, I understand."),
        ("no", "لا", "No, thank you."),
        ("water", "ماء", "I need a glass of water."),
        ("food", "طعام", "The food is delicious."),
        ("house", "بيت", "My house is near the school."),
        ("school", "مدرسة", "I go to school every day."),
        ("book", "كتاب", "This is my English book."),
        ("friend", "صديق", "She is my best friend."),
        ("family", "عائلة", "My family is very kind."),
        ("mother", "أم", "My mother cooks dinner."),
        ("father", "أب", "My father works in a shop."),
        ("day", "يوم", "Today is a sunny day."),
        ("night", "ليل", "Good night, sleep well."),
        ("big", "كبير", "The city is very big."),
        ("small", "صغير", "The cat is small."),
        ("happy", "سعيد", "I am happy today."),
    ],
    "A2": [
        ("weather", "طقس", "The weather is cold today."),
        ("travel", "سفر", "We travel by bus."),
        ("market", "سوق", "She buys fruit at the market."),
        ("doctor", "طبيب", "I visited the doctor yesterday."),
        ("exercise", "تمرين", "Exercise keeps you healthy."),
        ("holiday", "عطلة", "We had a holiday in July."),
        ("neighbor", "جار", "Our neighbor is friendly."),
        ("library", "مكتبة", "I study in the library."),
        ("ticket", "تذكرة", "He bought a train ticket."),
        ("garden", "حديقة", "Children play in the garden."),
        ("breakfast", "فطور", "I eat breakfast at seven."),
        ("problem", "مشكلة", "We solved the problem quickly."),
        ("answer", "إجابة", "Please write your answer here."),
        ("important", "مهم", "It is important to be on time."),
        ("different", "مختلف", "These two books are different."),
        ("expensive", "غالي", "The jacket is too expensive."),
        ("cheap", "رخيص", "This pen is cheap."),
        ("remember", "يتذكر", "I remember your name."),
        ("forget", "ينسى", "Don't forget your keys."),
        ("invite", "يدعو", "They invited us to dinner."),
    ],
    "B1": [
        ("environment", "بيئة", "We must protect the environment."),
        ("opportunity", "فرصة", "This job is a great opportunity."),
        ("decision", "قرار", "Making a decision can be difficult."),
        ("experience", "تجربة", "Travel gives you new experiences."),
        ("achievement", "إنجاز", "Graduation is a big achievement."),
        ("challenge", "تحدي", "Learning a language is a challenge."),
        ("research", "بحث", "She does research at the university."),
        ("technology", "تكنولوجيا", "Technology changes quickly."),
        ("communication", "تواصل", "Clear communication is essential."),
        ("volunteer", "متطوع", "He works as a volunteer."),
        ("deadline", "موعد نهائي", "We must meet the deadline."),
        ("negotiate", "يتفاوض", "They negotiated a better price."),
        ("perspective", "منظور", "Try to see it from my perspective."),
        ("consequence", "نتيجة", "Every action has a consequence."),
        ("efficient", "فعّال", "This method is more efficient."),
        ("evidence", "دليل", "The police found new evidence."),
        ("influence", "تأثير", "Teachers influence their students."),
        ("maintain", "يحافظ", "It is hard to maintain good habits."),
        ("priority", "أولوية", "Health should be a priority."),
        ("strategy", "استراتيجية", "We need a clear strategy."),
    ],
}

WRITING_PROMPTS = {
    "A1": [
        ("Describe your family.", "صف عائلتك.", 30, 2),
        ("Write about your daily routine.", "اكتب عن روتينك اليومي.", 35, 2),
        ("Describe your favorite food.", "صف طعامك المفضل.", 30, 2),
        ("Write about your home.", "اكتب عن منزلك.", 30, 2),
        ("Describe your best friend.", "صف صديقك المقرب.", 35, 2),
    ],
    "A2": [
        ("Write about a trip you took.", "اكتب عن رحلة قمت بها.", 50, 3),
        ("Describe a memorable day.", "صف يوماً لا يُنسى.", 50, 3),
        ("Write about your hobbies.", "اكتب عن هواياتك.", 45, 3),
        ("Describe your neighborhood.", "صف حيك.", 45, 3),
        ("Write about a book or film you like.", "اكتب عن كتاب أو فيلم أعجبك.", 55, 3),
    ],
    "B1": [
        ("Discuss the advantages of learning online.", "ناقش مزايا التعلم عبر الإنترنت.", 80, 4),
        ("Write about a problem in your city.", "اكتب عن مشكلة في مدينتك.", 80, 4),
        ("Describe a goal you want to achieve.", "صف هدفاً تريد تحقيقه.", 75, 4),
        ("Compare city life and country life.", "قارن بين الحياة في المدينة والريف.", 90, 4),
        ("Write about how technology affects daily life.", "اكتب عن تأثير التكنولوجيا على الحياة اليومية.", 85, 4),
    ],
}

SPEAKING_PROMPTS = {
    "A1": [
        ("Introduce yourself.", "عرّف عن نفسك.", 15),
        ("Describe your family.", "صف عائلتك.", 20),
        ("Talk about your favorite hobby.", "تحدث عن هوايتك المفضلة.", 20),
        ("Describe your daily routine.", "صف روتينك اليومي.", 20),
        ("Talk about your favorite food.", "تحدث عن طعامك المفضل.", 15),
    ],
    "A2": [
        ("Describe a place you visited.", "صف مكاناً زرته.", 25),
        ("Talk about a festival or celebration.", "تحدث عن مهرجان أو احتفال.", 25),
        ("Describe your job or studies.", "صف عملك أو دراستك.", 25),
        ("Talk about a skill you want to learn.", "تحدث عن مهارة تريد تعلمها.", 25),
        ("Describe your ideal weekend.", "صف عطلة نهاية الأسبوع المثالية.", 25),
    ],
    "B1": [
        ("Discuss environmental issues.", "ناقش القضايا البيئية.", 30),
        ("Talk about a challenge you overcame.", "تحدث عن تحدٍ تجاوزته.", 30),
        ("Describe your career goals.", "صف أهدافك المهنية.", 30),
        ("Discuss social media effects.", "ناقش تأثيرات وسائل التواصل.", 30),
        ("Talk about cultural differences.", "تحدث عن الاختلافات الثقافية.", 30),
    ],
}


def upgrade() -> None:
    bind = op.get_bind()
    language_vocabulary_status.create(bind, checkfirst=True)

    op.add_column(
        "language_vocabulary_progress",
        sa.Column(
            "status",
            language_vocabulary_status,
            server_default=sa.text("'new'"),
            nullable=False,
        ),
    )
    op.add_column(
        "language_vocabulary_progress",
        sa.Column("review_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "language_vocabulary_progress",
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column("language_writing_progress", sa.Column("score_percent", sa.Float(), nullable=True))
    op.add_column("language_writing_progress", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_language_writing_progress", "language_writing_progress", ["student_id", "content_item_id"])

    op.add_column("language_speaking_progress", sa.Column("duration_seconds", sa.Integer(), nullable=True))
    op.add_column("language_speaking_progress", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_language_speaking_progress", "language_speaking_progress", ["student_id", "content_item_id"])

    lang_id = bind.execute(sa.text("SELECT id FROM languages WHERE code = 'en' LIMIT 1")).scalar()
    if not lang_id:
        return

    for level in LEVELS:
        for i, (word, trans, example) in enumerate(VOCAB_BANK[level], start=1):
            seed_key = f"c2_vocab_{level.lower()}_{i:02d}"
            if bind.execute(
                sa.text("SELECT 1 FROM language_content_items WHERE body_json->>'seed_key' = :k LIMIT 1"),
                {"k": seed_key},
            ).scalar():
                continue
            body = {
                "seed_key": seed_key,
                "word": word,
                "translation_ar": trans,
                "example": example,
            }
            bind.execute(
                sa.text(
                    """
                    INSERT INTO language_content_items
                      (language_id, skill, level, content_type, title, body_json, sort_order, is_published)
                    VALUES
                      (:lang_id, 'reading', :level, 'vocabulary', :title, CAST(:body AS jsonb), :sort_order, true)
                    """
                ),
                {
                    "lang_id": lang_id,
                    "level": level,
                    "title": f"Vocabulary {level} — {word}",
                    "body": json.dumps(body),
                    "sort_order": i,
                },
            )

    for level in LEVELS:
        for i, (prompt, prompt_ar, min_words, min_sentences) in enumerate(WRITING_PROMPTS[level], start=1):
            seed_key = f"c2_writing_{level.lower()}_{i:02d}"
            if bind.execute(
                sa.text("SELECT 1 FROM language_content_items WHERE body_json->>'seed_key' = :k LIMIT 1"),
                {"k": seed_key},
            ).scalar():
                continue
            body = {
                "seed_key": seed_key,
                "prompt": prompt,
                "prompt_ar": prompt_ar,
                "min_words": min_words,
                "min_sentences": min_sentences,
                "pass_threshold_percent": 70,
            }
            bind.execute(
                sa.text(
                    """
                    INSERT INTO language_content_items
                      (language_id, skill, level, content_type, title, body_json, sort_order, is_published)
                    VALUES
                      (:lang_id, 'writing', :level, 'writing_prompt', :title, CAST(:body AS jsonb), :sort_order, true)
                    """
                ),
                {
                    "lang_id": lang_id,
                    "level": level,
                    "title": f"Writing {level} — Prompt {i}",
                    "body": json.dumps(body),
                    "sort_order": i,
                },
            )

    for level in LEVELS:
        for i, (prompt, prompt_ar, min_seconds) in enumerate(SPEAKING_PROMPTS[level], start=1):
            seed_key = f"c2_speaking_{level.lower()}_{i:02d}"
            if bind.execute(
                sa.text("SELECT 1 FROM language_content_items WHERE body_json->>'seed_key' = :k LIMIT 1"),
                {"k": seed_key},
            ).scalar():
                continue
            body = {
                "seed_key": seed_key,
                "prompt": prompt,
                "prompt_ar": prompt_ar,
                "min_seconds": min_seconds,
                "pass_threshold_percent": 70,
            }
            bind.execute(
                sa.text(
                    """
                    INSERT INTO language_content_items
                      (language_id, skill, level, content_type, title, body_json, sort_order, is_published)
                    VALUES
                      (:lang_id, 'speaking', :level, 'speaking_prompt', :title, CAST(:body AS jsonb), :sort_order, true)
                    """
                ),
                {
                    "lang_id": lang_id,
                    "level": level,
                    "title": f"Speaking {level} — Prompt {i}",
                    "body": json.dumps(body),
                    "sort_order": i,
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM language_content_items WHERE body_json->>'seed_key' LIKE 'c2_%'"))

    op.drop_constraint("uq_language_speaking_progress", "language_speaking_progress", type_="unique")
    op.drop_column("language_speaking_progress", "completed_at")
    op.drop_column("language_speaking_progress", "duration_seconds")

    op.drop_constraint("uq_language_writing_progress", "language_writing_progress", type_="unique")
    op.drop_column("language_writing_progress", "completed_at")
    op.drop_column("language_writing_progress", "score_percent")

    op.drop_column("language_vocabulary_progress", "last_reviewed_at")
    op.drop_column("language_vocabulary_progress", "review_count")
    op.drop_column("language_vocabulary_progress", "status")

    language_vocabulary_status.drop(bind, checkfirst=True)
