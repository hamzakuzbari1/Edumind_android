"""Conversation scenarios table, session link, and Phase 7.7 seeds.

Revision ID: 0045_conversation_scenarios
Revises: 0044_language_analytics_achievements
"""
import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0045_conversation_scenarios"
down_revision = "0044_language_analytics_achievements"
branch_labels = None
depends_on = None

language_level = postgresql.ENUM(
    "A1", "A2", "B1", "B2", "C1", "C2", name="language_level", create_type=False
)

SCENARIOS = [
    {
        "scenario_key": "airport_checkin",
        "category": "airport",
        "title_en": "Airport Immigration",
        "title_ar": "الجوازات في المطار",
        "description_en": "Answer simple questions at passport control. Show your passport and explain why you are visiting.",
        "description_ar": "جاوب على أسئلة بسيطة عند الجوازات. ورّي جوازك واشرح ليش مسافر.",
        "level_min": "A1",
        "target_skills": ["speaking", "listening", "vocabulary"],
        "ai_role": "an airport immigration officer",
        "student_role": "a traveler arriving at the airport",
        "opening_line": "Good morning. Passport, please. Where are you flying from today?",
        "sort_order": 0,
    },
    {
        "scenario_key": "hotel_reception",
        "category": "hotel",
        "title_en": "Hotel Check-in",
        "title_ar": "تسجيل الدخول بالفندق",
        "description_en": "Check in at the hotel desk, give your name, and ask about your room and breakfast.",
        "description_ar": "سجّل دخولك عند استقبال الفندق، قدّم اسمك، واسأل عن الغرفة والإفطار.",
        "level_min": "A2",
        "target_skills": ["speaking", "listening", "vocabulary"],
        "ai_role": "a hotel receptionist",
        "student_role": "a guest checking in",
        "opening_line": "Hello, welcome to the Grand Hotel. Do you have a reservation with us?",
        "sort_order": 1,
    },
    {
        "scenario_key": "restaurant_order",
        "category": "restaurant",
        "title_en": "Ordering at a Restaurant",
        "title_ar": "الطلب في المطعم",
        "description_en": "Order food and drinks, ask about ingredients, and request the bill.",
        "description_ar": "اطلب أكل ومشروبات، اسأل عن المكونات، واطلب الفاتورة.",
        "level_min": "A2",
        "target_skills": ["speaking", "vocabulary", "fluency"],
        "ai_role": "a restaurant server",
        "student_role": "a customer at a restaurant",
        "opening_line": "Hi there! Welcome. Are you ready to order, or do you need a few more minutes with the menu?",
        "sort_order": 2,
    },
    {
        "scenario_key": "university_admissions",
        "category": "university",
        "title_en": "University Admissions Office",
        "title_ar": "مكتب القبول الجامعي",
        "description_en": "Discuss your study program, entry requirements, deadlines, and required documents in detail.",
        "description_ar": "ناقش التخصص، شروط القبول، المواعيد النهائية، والأوراق المطلوبة بالتفصيل.",
        "level_min": "B2",
        "target_skills": ["speaking", "fluency", "grammar"],
        "ai_role": "a university admissions officer",
        "student_role": "a prospective international student",
        "opening_line": "Good afternoon. Thanks for coming in. Which program are you applying for, and what motivated you to choose it?",
        "sort_order": 3,
    },
    {
        "scenario_key": "job_interview",
        "category": "job_interview",
        "title_en": "Job Interview",
        "title_ar": "مقابلة عمل",
        "description_en": "Introduce yourself, describe your experience, and answer interview questions professionally.",
        "description_ar": "عرّف عن حالك، احكي عن خبرتك، وجاوب على أسئلة المقابلة باحترافية.",
        "level_min": "B1",
        "target_skills": ["speaking", "fluency", "grammar"],
        "ai_role": "a hiring manager",
        "student_role": "a job applicant",
        "opening_line": "Good morning, thank you for coming in. Please, have a seat. Could you tell me a little about yourself?",
        "sort_order": 4,
    },
    {
        "scenario_key": "doctor_visit",
        "category": "doctor",
        "title_en": "Doctor Visit",
        "title_ar": "زيارة الدكتور",
        "description_en": "Describe your symptoms, answer the doctor's questions, and ask about treatment.",
        "description_ar": "وصف أعراضك، جاوب على أسئلة الدكتور، واسأل عن العلاج.",
        "level_min": "A2",
        "target_skills": ["speaking", "vocabulary", "listening"],
        "ai_role": "a doctor",
        "student_role": "a patient",
        "opening_line": "Hello, please come in. What seems to be the problem today? How long have you felt this way?",
        "sort_order": 5,
    },
    {
        "scenario_key": "daily_shopping",
        "category": "shopping",
        "title_en": "Daily Shopping",
        "title_ar": "تسوّق يومي",
        "description_en": "Buy groceries, ask for help finding items, and pay at the checkout.",
        "description_ar": "اشتري غراضك، اطلب مساعدة للعثور على منتج، وادفع عند الكاشير.",
        "level_min": "A1",
        "target_skills": ["speaking", "vocabulary", "listening"],
        "ai_role": "a shop assistant",
        "student_role": "a customer shopping for groceries",
        "opening_line": "Hello! Can I help you find anything today?",
        "sort_order": 6,
    },
    {
        "scenario_key": "daily_conversation",
        "category": "daily_conversation",
        "title_en": "Daily Conversation",
        "title_ar": "محادثة يومية",
        "description_en": "Chat with a neighbor about your day, the weather, and weekend plans.",
        "description_ar": "احكي مع جارك عن يومك، الطقس، وخطط نهاية الأسبوع.",
        "level_min": "A1",
        "target_skills": ["speaking", "fluency", "vocabulary"],
        "ai_role": "a friendly neighbor",
        "student_role": "a neighbor you just met",
        "opening_line": "Hi! Nice to meet you. I'm Alex from next door. How's your day going so far?",
        "sort_order": 7,
    },
]


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t LIMIT 1"),
        {"t": table},
    ).fetchone()
    return row is not None


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
    if not _table_exists(conn, "language_conversation_scenarios"):
        op.create_table(
            "language_conversation_scenarios",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("language_id", sa.Integer(), nullable=False),
            sa.Column("scenario_key", sa.String(length=64), nullable=False),
            sa.Column("category", sa.String(length=32), server_default="daily_conversation", nullable=False),
            sa.Column("title_en", sa.String(length=200), nullable=False),
            sa.Column("title_ar", sa.String(length=200), nullable=False),
            sa.Column("description_en", sa.Text(), nullable=True),
            sa.Column("description_ar", sa.Text(), nullable=True),
            sa.Column("level_min", language_level, nullable=False),
            sa.Column("ai_role", sa.String(length=200), nullable=False),
            sa.Column("student_role", sa.String(length=200), nullable=False),
            sa.Column("opening_line", sa.Text(), nullable=False),
            sa.Column(
                "target_skills_json",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=False,
            ),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
            sa.ForeignKeyConstraint(["language_id"], ["languages.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("language_id", "scenario_key", name="uq_lang_conversation_scenario_key"),
        )

    if not _column_exists(conn, "language_speaking_conversation_sessions", "scenario_id"):
        op.add_column(
            "language_speaking_conversation_sessions",
            sa.Column("scenario_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_conversation_session_scenario",
            "language_speaking_conversation_sessions",
            "language_conversation_scenarios",
            ["scenario_id"],
            ["id"],
            ondelete="SET NULL",
        )

    row = conn.execute(sa.text("SELECT id FROM languages WHERE code = 'en' LIMIT 1")).fetchone()
    if not row:
        return
    lang_id = row[0]

    for s in SCENARIOS:
        skills_json = json.dumps(s["target_skills"])
        exists = conn.execute(
            sa.text(
                "SELECT id FROM language_conversation_scenarios "
                "WHERE language_id = :lang AND scenario_key = :key LIMIT 1"
            ),
            {"lang": lang_id, "key": s["scenario_key"]},
        ).fetchone()
        if exists:
            conn.execute(
                sa.text(
                    "UPDATE language_conversation_scenarios SET "
                    "category = :cat, title_en = :ten, title_ar = :tar, "
                    "description_en = :den, description_ar = :dar, "
                    "level_min = cast(:lvl as language_level), ai_role = :ai, student_role = :stu, "
                    "opening_line = :open, is_active = true, sort_order = :sort, "
                    "target_skills_json = cast(:skills as jsonb) "
                    "WHERE id = :id"
                ),
                {
                    "id": exists[0],
                    "cat": s["category"],
                    "ten": s["title_en"],
                    "tar": s["title_ar"],
                    "den": s["description_en"],
                    "dar": s["description_ar"],
                    "lvl": s["level_min"],
                    "ai": s["ai_role"],
                    "stu": s["student_role"],
                    "open": s["opening_line"],
                    "sort": s["sort_order"],
                    "skills": skills_json,
                },
            )
            continue
        conn.execute(
            sa.text(
                "INSERT INTO language_conversation_scenarios "
                "(language_id, scenario_key, category, title_en, title_ar, description_en, description_ar, "
                "level_min, ai_role, student_role, opening_line, is_active, sort_order, target_skills_json) "
                "VALUES (:lang, :key, :cat, :ten, :tar, :den, :dar, cast(:lvl as language_level), "
                ":ai, :stu, :open, true, :sort, cast(:skills as jsonb))"
            ),
            {
                "lang": lang_id,
                "key": s["scenario_key"],
                "cat": s["category"],
                "ten": s["title_en"],
                "tar": s["title_ar"],
                "den": s["description_en"],
                "dar": s["description_ar"],
                "lvl": s["level_min"],
                "ai": s["ai_role"],
                "stu": s["student_role"],
                "open": s["opening_line"],
                "sort": s["sort_order"],
                "skills": skills_json,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "language_speaking_conversation_sessions", "scenario_id"):
        op.drop_constraint(
            "fk_conversation_session_scenario",
            "language_speaking_conversation_sessions",
            type_="foreignkey",
        )
        op.drop_column("language_speaking_conversation_sessions", "scenario_id")
    if _table_exists(conn, "language_conversation_scenarios"):
        op.drop_table("language_conversation_scenarios")
