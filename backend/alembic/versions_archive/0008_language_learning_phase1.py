"""Language Learning Phase 1 — schema, payment_items extension, catalog seed."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_language_learning_phase1"
down_revision = "0007_subscription_lifecycle"
branch_labels = None
depends_on = None

language_skill = postgresql.ENUM(
    "reading", "listening", "writing", "speaking", name="language_skill", create_type=False
)
language_level = postgresql.ENUM(
    "A1", "A2", "B1", "B2", "C1", "C2", name="language_level", create_type=False
)
language_onboarding_step = postgresql.ENUM(
    "select_language", "placement", "dashboard", name="language_onboarding_step", create_type=False
)
language_placement_attempt_status = postgresql.ENUM(
    "in_progress", "submitted", "abandoned", name="language_placement_attempt_status", create_type=False
)
language_content_progress_status = postgresql.ENUM(
    "not_started", "in_progress", "completed", name="language_content_progress_status", create_type=False
)
payment_item_product_type = postgresql.ENUM(
    "course", "language", name="payment_item_product_type", create_type=False
)
paymentstatus = postgresql.ENUM("pending", "paid", "failed", name="paymentstatus", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    language_skill.create(bind, checkfirst=True)
    language_level.create(bind, checkfirst=True)
    language_onboarding_step.create(bind, checkfirst=True)
    language_placement_attempt_status.create(bind, checkfirst=True)
    language_content_progress_status.create(bind, checkfirst=True)
    payment_item_product_type.create(bind, checkfirst=True)

    op.create_table(
        "languages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("name_en", sa.String(120), nullable=False),
        sa.Column("name_ar", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_languages_code", "languages", ["code"], unique=True)

    op.create_table(
        "language_products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name_ar", sa.String(200), nullable=False),
        sa.Column("description_ar", sa.String(1000), nullable=True),
        sa.Column("price", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("currency", sa.String(10), server_default=sa.text("'SYP'"), nullable=False),
        sa.Column("term_days", sa.Integer(), server_default=sa.text("365"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_language_products_slug", "language_products", ["slug"], unique=True)

    op.create_table(
        "language_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("language_products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payment_status", paymentstatus, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("student_id", "product_id", name="uq_language_subscription_student_product"),
    )
    op.create_index("ix_language_subscriptions_student_id", "language_subscriptions", ["student_id"])
    op.create_index("ix_language_subscriptions_expires_at", "language_subscriptions", ["expires_at"])

    op.create_table(
        "language_student_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("onboarding_step", language_onboarding_step, server_default=sa.text("'select_language'"), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("placement_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_assessment_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_allowed_retake_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("target_level", language_level, nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("certificate_level", language_level, nullable=True),
        sa.Column("certificate_awarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_time_to_next_level", sa.String(64), nullable=True),
        sa.Column("target_progress_percent", sa.Integer(), nullable=True),
        sa.Column("preferences_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("student_id", "language_id", name="uq_language_student_profile"),
    )

    op.create_table(
        "language_placement_sections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill", language_skill, nullable=False),
        sa.Column("title_ar", sa.String(200), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )

    op.create_table(
        "language_placement_questions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("language_placement_sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_type", sa.String(32), nullable=False),
        sa.Column("prompt_json", postgresql.JSONB(), nullable=False),
        sa.Column("media_url", sa.String(1024), nullable=True),
        sa.Column("answer_key_json", postgresql.JSONB(), nullable=True),
        sa.Column("max_points", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("level_hint", sa.String(8), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )

    op.create_table(
        "language_placement_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", language_placement_attempt_status, server_default=sa.text("'in_progress'"), nullable=False),
        sa.Column("is_retake", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "language_placement_responses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("language_placement_attempts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("language_placement_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("response_json", postgresql.JSONB(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("evaluation_metadata", postgresql.JSONB(), nullable=True),
    )

    op.create_table(
        "language_assessments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("language_placement_attempts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("overall_level", language_level, nullable=True),
        sa.Column("overall_calculation_method", sa.String(32), server_default=sa.text("'bottleneck'"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "language_assessment_skill_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("language_assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill", language_skill, nullable=False),
        sa.Column("score_percent", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("level", language_level, nullable=False),
        sa.Column("raw_metrics_json", postgresql.JSONB(), nullable=True),
        sa.Column("ai_evaluation_json", postgresql.JSONB(), nullable=True),
    )

    op.create_table(
        "language_learning_paths",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_id", sa.Integer(), sa.ForeignKey("language_assessments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("overall_level", language_level, nullable=True),
        sa.Column("path_json", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "language_content_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill", language_skill, nullable=False),
        sa.Column("level", language_level, nullable=False),
        sa.Column("content_type", sa.String(32), server_default=sa.text("'lesson'"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body_json", postgresql.JSONB(), nullable=True),
        sa.Column("media_object_id", sa.Integer(), sa.ForeignKey("media_objects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "language_path_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("path_id", sa.Integer(), sa.ForeignKey("language_learning_paths.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill", language_skill, nullable=False),
        sa.Column("level", language_level, nullable=False),
        sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("language_content_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", language_content_progress_status, server_default=sa.text("'not_started'"), nullable=False),
    )

    op.create_table(
        "language_reading_progress",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("language_content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", language_content_progress_status, server_default=sa.text("'not_started'"), nullable=False),
        sa.Column("score_percent", sa.Float(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("student_id", "content_item_id", name="uq_language_reading_progress"),
    )

    op.create_table(
        "language_listening_progress",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("language_content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", language_content_progress_status, server_default=sa.text("'not_started'"), nullable=False),
        sa.Column("score_percent", sa.Float(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("student_id", "content_item_id", name="uq_language_listening_progress"),
    )

    op.create_table(
        "language_writing_progress",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("language_content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submitted_text", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("metrics_json", postgresql.JSONB(), nullable=True),
        sa.Column("level_estimate", language_level, nullable=True),
        sa.Column("scoring_version", sa.String(32), server_default=sa.text("'rule_v1'"), nullable=False),
        sa.Column("ai_evaluation_json", postgresql.JSONB(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "language_speaking_progress",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_item_id", sa.Integer(), sa.ForeignKey("language_content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_object_id", sa.Integer(), sa.ForeignKey("media_objects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("metrics_json", postgresql.JSONB(), nullable=True),
        sa.Column("level_estimate", language_level, nullable=True),
        sa.Column("scoring_version", sa.String(32), server_default=sa.text("'rule_v1'"), nullable=False),
        sa.Column("ai_evaluation_json", postgresql.JSONB(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "language_vocabulary_progress",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lemma", sa.String(120), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("mastery_score", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.UniqueConstraint("student_id", "language_id", "lemma", name="uq_language_vocab"),
    )

    op.create_table(
        "language_streaks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("current_streak", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("longest_streak", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_activity_date", sa.Date(), nullable=True),
        sa.UniqueConstraint("student_id", "language_id", name="uq_language_streak"),
    )

    op.create_table(
        "language_activity_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("skill", language_skill, nullable=True),
        sa.Column("duration_seconds", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_language_activity_log_student_created", "language_activity_log", ["student_id", "created_at"])

    op.create_table(
        "language_analytics",
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("reading_level", language_level, nullable=True),
        sa.Column("listening_level", language_level, nullable=True),
        sa.Column("writing_level", language_level, nullable=True),
        sa.Column("speaking_level", language_level, nullable=True),
        sa.Column("overall_level_internal", language_level, nullable=True),
        sa.Column("primary_focus_skill", sa.String(32), nullable=True),
        sa.Column("strength_skill", sa.String(32), nullable=True),
        sa.Column("vocabulary_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("estimated_time_to_next_level", sa.String(64), nullable=True),
        sa.Column("target_progress_percent", sa.Integer(), nullable=True),
        sa.Column("weekly_minutes_json", postgresql.JSONB(), nullable=True),
        sa.Column("skill_growth_json", postgresql.JSONB(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # payment_items extension
    op.add_column(
        "payment_items",
        sa.Column("product_type", payment_item_product_type, server_default=sa.text("'course'"), nullable=False),
    )
    op.add_column(
        "payment_items",
        sa.Column("language_product_id", sa.Integer(), sa.ForeignKey("language_products.id", ondelete="CASCADE"), nullable=True),
    )
    op.alter_column("payment_items", "course_id", existing_type=sa.Integer(), nullable=True)
    op.create_check_constraint(
        "ck_payment_items_product_target",
        "payment_items",
        "(product_type = 'course' AND course_id IS NOT NULL AND language_product_id IS NULL) OR "
        "(product_type = 'language' AND language_product_id IS NOT NULL AND course_id IS NULL)",
    )

    # Seed catalog
    op.execute(
        sa.text(
            """
            INSERT INTO languages (code, name_en, name_ar, is_active)
            SELECT 'en', 'English', 'الإنجليزية', true
            WHERE NOT EXISTS (SELECT 1 FROM languages WHERE code = 'en')
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO language_products (slug, name_ar, description_ar, price, currency, term_days, is_active)
            SELECT 'language_learning', 'اشتراك تعلّم اللغة', 'تعلّم الإنجليزية — قراءة، استماع، كتابة، وتحدث', 150000, 'SYP', 365, true
            WHERE NOT EXISTS (SELECT 1 FROM language_products WHERE slug = 'language_learning')
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("ck_payment_items_product_target", "payment_items", type_="check")
    op.drop_column("payment_items", "language_product_id")
    op.drop_column("payment_items", "product_type")
    op.alter_column("payment_items", "course_id", existing_type=sa.Integer(), nullable=False)

    for table in (
        "language_analytics",
        "language_activity_log",
        "language_streaks",
        "language_vocabulary_progress",
        "language_speaking_progress",
        "language_writing_progress",
        "language_listening_progress",
        "language_reading_progress",
        "language_path_items",
        "language_content_items",
        "language_learning_paths",
        "language_assessment_skill_scores",
        "language_assessments",
        "language_placement_responses",
        "language_placement_attempts",
        "language_placement_questions",
        "language_placement_sections",
        "language_student_profiles",
        "language_subscriptions",
        "language_products",
        "languages",
    ):
        op.drop_table(table)

    bind = op.get_bind()
    for enum_type in (
        payment_item_product_type,
        language_content_progress_status,
        language_placement_attempt_status,
        language_onboarding_step,
        language_level,
        language_skill,
    ):
        enum_type.drop(bind, checkfirst=True)
