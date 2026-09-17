"""Language Learning Phase 2 — placement wiring + certificates + seed bank.

Revision: 0009_language_phase2
Revises: 0008_language_learning_phase1
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_language_phase2"
down_revision = "0008_language_learning_phase1"
branch_labels = None
depends_on = None

language_level = postgresql.ENUM(
    "A1", "A2", "B1", "B2", "C1", "C2", name="language_level", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    language_level.create(bind, checkfirst=True)

    # Certificates (foundation only: no PDF generation, no UI).
    op.create_table(
        "language_certificates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("certificate_level", language_level, nullable=False),
        sa.Column("certificate_number", sa.String(64), nullable=False),
        sa.Column("verification_code", sa.String(64), nullable=False),
        sa.Column("certificate_status", sa.String(32), server_default=sa.text("'issued'"), nullable=False),
        sa.Column("verification_url", sa.String(2048), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("pdf_url", sa.String(2048), nullable=True),
    )
    op.create_index(
        "ix_language_certificates_student_language",
        "language_certificates",
        ["student_id", "language_id"],
    )
    op.create_index("ix_language_certificates_number", "language_certificates", ["certificate_number"], unique=True)
    op.create_index("ix_language_certificates_code", "language_certificates", ["verification_code"], unique=True)

    # Autosave safety: ensure only one response per question per attempt.
    op.create_unique_constraint(
        "uq_language_placement_attempt_question",
        "language_placement_responses",
        ["attempt_id", "question_id"],
    )

    # Seed English placement bank (portable audio: media_objects points to stable URLs).
    # NOTE: We only seed URLs + metadata; actual audio files can be served by any environment that
    # hosts these URLs (frontend public assets, CDN, etc.). This keeps DB portable.
    op.execute(
        """
        INSERT INTO language_placement_sections (language_id, skill, title_ar, sort_order)
        SELECT l.id, s.skill::language_skill, s.title_ar, s.sort_order
        FROM languages l
        JOIN (
          VALUES
            ('reading','القراءة',0),
            ('listening','الاستماع',1),
            ('writing','الكتابة',2),
            ('speaking','التحدث',3)
        ) AS s(skill, title_ar, sort_order) ON TRUE
        WHERE l.code = 'en'
          AND NOT EXISTS (
            SELECT 1 FROM language_placement_sections x WHERE x.language_id = l.id
          );
        """
    )

    # Seed listening audio media objects (10). Storage key is descriptive; public_url is environment-portable.
    op.execute(
        """
        INSERT INTO media_objects (storage_provider, storage_key, public_url, mime_type, original_filename)
        SELECT
          'local',
          'language/en/placement/listening/q' || n || '.mp3',
          '/language-assets/en/placement/listening/q' || n || '.mp3',
          'audio/mpeg',
          'q' || n || '.mp3'
        FROM generate_series(1, 10) AS n
        WHERE NOT EXISTS (
          SELECT 1 FROM media_objects mo
          WHERE mo.storage_key = 'language/en/placement/listening/q' || n || '.mp3'
        );
        """
    )

    # Reading questions (10) — MCQ vocabulary + comprehension.
    op.execute(
        """
        WITH lang AS (
          SELECT id AS language_id FROM languages WHERE code='en' LIMIT 1
        ),
        sec AS (
          SELECT s.id AS section_id
          FROM language_placement_sections s
          JOIN lang ON lang.language_id = s.language_id
          WHERE s.skill='reading'
          LIMIT 1
        )
        INSERT INTO language_placement_questions (section_id, question_type, prompt_json, media_url, answer_key_json, max_points, level_hint, sort_order)
        SELECT
          sec.section_id,
          'mcq',
          jsonb_build_object(
            'stem', q.stem,
            'choices', q.choices
          ),
          NULL,
          jsonb_build_object('correct_index', q.correct_index),
          1,
          q.level_hint,
          q.sort_order
        FROM sec
        JOIN (
          VALUES
            (0,'Choose the correct meaning of: \"rapid\"','[\"slow\",\"quick\",\"tired\",\"empty\"]'::jsonb,1,'A1'),
            (1,'Choose the correct word to complete: \"I ___ to school every day.\"','[\"go\",\"goes\",\"going\",\"gone\"]'::jsonb,0,'A1'),
            (2,'Choose the correct meaning of: \"accurate\"','[\"wrong\",\"exact\",\"small\",\"loud\"]'::jsonb,1,'A2'),
            (3,'Which sentence is correct?','[\"She don\\u2019t like apples.\",\"She doesn\\u2019t likes apples.\",\"She doesn\\u2019t like apple.\",\"She not like apples.\"]'::jsonb,0,'A2'),
            (4,'Short text: \"Tom missed the bus, so he arrived late.\" Why was Tom late?','[\"He missed the bus.\",\"He lost his keys.\",\"He woke up early.\",\"He ran fast.\"]'::jsonb,0,'B1'),
            (5,'Choose the best synonym for: \"maintain\"','[\"repair\",\"keep\",\"discover\",\"forget\"]'::jsonb,1,'B1'),
            (6,'In a notice: \"Students must submit assignments by Friday.\" What is required?','[\"Submit by Friday\",\"Read by Friday\",\"Pay by Friday\",\"Travel by Friday\"]'::jsonb,0,'B1'),
            (7,'Choose the best word: \"Although it was raining, we ___ the match.\"','[\"cancel\",\"continued\",\"stop\",\"stopped\"]'::jsonb,1,'B2'),
            (8,'Which is closest to: \"The results were inconclusive\"?','[\"The results were clear\",\"The results were uncertain\",\"The results were perfect\",\"The results were final\"]'::jsonb,1,'C1'),
            (9,'Choose the best paraphrase: \"He was reluctant to accept.\"','[\"He agreed immediately\",\"He was hesitant\",\"He refused forever\",\"He was excited\"]'::jsonb,1,'C1')
        ) AS q(sort_order, stem, choices, correct_index, level_hint) ON TRUE
        WHERE NOT EXISTS (
          SELECT 1 FROM language_placement_questions qp WHERE qp.section_id = sec.section_id
        );
        """
    )

    # Listening questions (10) — MCQ. Media URL resolved from media_objects public_url.
    op.execute(
        """
        WITH lang AS (
          SELECT id AS language_id FROM languages WHERE code='en' LIMIT 1
        ),
        sec AS (
          SELECT s.id AS section_id
          FROM language_placement_sections s
          JOIN lang ON lang.language_id = s.language_id
          WHERE s.skill='listening'
          LIMIT 1
        ),
        aud AS (
          SELECT
            n,
            (SELECT public_url FROM media_objects WHERE storage_key = 'language/en/placement/listening/q' || n || '.mp3' LIMIT 1) AS url
          FROM generate_series(1, 10) AS n
        )
        INSERT INTO language_placement_questions (section_id, question_type, prompt_json, media_url, answer_key_json, max_points, level_hint, sort_order)
        SELECT
          sec.section_id,
          'mcq_listening',
          jsonb_build_object(
            'stem', q.stem,
            'choices', q.choices,
            'audio_media_storage_key', 'language/en/placement/listening/q' || q.n || '.mp3'
          ),
          aud.url,
          jsonb_build_object('correct_index', q.correct_index),
          1,
          q.level_hint,
          q.sort_order
        FROM sec
        JOIN (
          VALUES
            (1,0,'You hear: \"Open your books.\" What should you do?','[\"Close your books\",\"Open your books\",\"Stand up\",\"Go home\"]'::jsonb,1,'A1',1),
            (2,1,'You hear: \"I\\u2019m hungry.\" What does it mean?','[\"I want food\",\"I\\u2019m tired\",\"I\\u2019m angry\",\"I\\u2019m late\"]'::jsonb,0,'A1',2),
            (3,2,'You hear: \"Turn left at the corner.\" What direction?','[\"Left\",\"Right\",\"Straight\",\"Back\"]'::jsonb,0,'A2',3),
            (4,3,'You hear: \"She has been studying for two hours.\" When did she start?','[\"Two hours ago\",\"In two hours\",\"Yesterday\",\"Next week\"]'::jsonb,0,'B1',4),
            (5,4,'You hear: \"The meeting was postponed.\" What happened?','[\"It was cancelled\",\"It was delayed\",\"It started early\",\"It ended\"]'::jsonb,1,'B1',5),
            (6,5,'You hear: \"He apologized for the inconvenience.\" Why?','[\"He is proud\",\"He is sorry\",\"He is bored\",\"He is hungry\"]'::jsonb,1,'B2',6),
            (7,6,'You hear: \"The device malfunctioned.\" What does it mean?','[\"It worked well\",\"It broke\",\"It was expensive\",\"It was new\"]'::jsonb,1,'B2',7),
            (8,7,'You hear: \"Her argument was compelling.\" How was it?','[\"Weak\",\"Convincing\",\"Funny\",\"Short\"]'::jsonb,1,'C1',8),
            (9,8,'You hear: \"The data was ambiguous.\" What does it imply?','[\"Clear\",\"Uncertain\",\"Perfect\",\"Old\"]'::jsonb,1,'C1',9),
            (10,9,'You hear: \"The outcome was unprecedented.\" What does it mean?','[\"Never happened before\",\"Very common\",\"Very small\",\"Very fast\"]'::jsonb,0,'C2',10)
        ) AS q(n, sort_order, stem, choices, correct_index, level_hint, idx) ON TRUE
        JOIN aud ON aud.n = q.n
        WHERE NOT EXISTS (
          SELECT 1 FROM language_placement_questions qp WHERE qp.section_id = sec.section_id
        );
        """
    )

    # Writing tasks (3).
    op.execute(
        """
        WITH lang AS (
          SELECT id AS language_id FROM languages WHERE code='en' LIMIT 1
        ),
        sec AS (
          SELECT s.id AS section_id
          FROM language_placement_sections s
          JOIN lang ON lang.language_id = s.language_id
          WHERE s.skill='writing'
          LIMIT 1
        )
        INSERT INTO language_placement_questions (section_id, question_type, prompt_json, media_url, answer_key_json, max_points, level_hint, sort_order)
        SELECT
          sec.section_id,
          'writing',
          jsonb_build_object('prompt', q.prompt, 'min_words', q.min_words),
          NULL,
          NULL,
          10,
          q.level_hint,
          q.sort_order
        FROM sec
        JOIN (
          VALUES
            (0,'Write 2-3 sentences about yourself.',20,'A1'),
            (1,'Write a short paragraph about your daily routine.',50,'A2'),
            (2,'Write an opinion (5-7 sentences): Should students wear uniforms?',80,'B1')
        ) AS q(sort_order, prompt, min_words, level_hint) ON TRUE
        WHERE NOT EXISTS (
          SELECT 1 FROM language_placement_questions qp WHERE qp.section_id = sec.section_id
        );
        """
    )

    # Speaking prompts (3). Recording is stored as media_object_id in placement responses (no paths/urls stored there).
    op.execute(
        """
        WITH lang AS (
          SELECT id AS language_id FROM languages WHERE code='en' LIMIT 1
        ),
        sec AS (
          SELECT s.id AS section_id
          FROM language_placement_sections s
          JOIN lang ON lang.language_id = s.language_id
          WHERE s.skill='speaking'
          LIMIT 1
        )
        INSERT INTO language_placement_questions (section_id, question_type, prompt_json, media_url, answer_key_json, max_points, level_hint, sort_order)
        SELECT
          sec.section_id,
          'speaking',
          jsonb_build_object('prompt', q.prompt, 'min_seconds', q.min_seconds),
          NULL,
          NULL,
          10,
          q.level_hint,
          q.sort_order
        FROM sec
        JOIN (
          VALUES
            (0,'Introduce yourself (name, age, school).',20,'A1'),
            (1,'Describe your favorite hobby and why you like it.',30,'A2'),
            (2,'Explain a challenge you faced and how you solved it.',45,'B1')
        ) AS q(sort_order, prompt, min_seconds, level_hint) ON TRUE
        WHERE NOT EXISTS (
          SELECT 1 FROM language_placement_questions qp WHERE qp.section_id = sec.section_id
        );
        """
    )


def downgrade() -> None:
    op.drop_constraint("uq_language_placement_attempt_question", "language_placement_responses", type_="unique")
    op.drop_index("ix_language_certificates_code", table_name="language_certificates")
    op.drop_index("ix_language_certificates_number", table_name="language_certificates")
    op.drop_index("ix_language_certificates_student_language", table_name="language_certificates")
    op.drop_table("language_certificates")
