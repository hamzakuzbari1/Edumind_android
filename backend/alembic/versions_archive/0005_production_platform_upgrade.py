"""Production platform upgrade: audit, sessions, media, analytics, AI queue, roles, indexes.

Revision ID: 0005_production_platform
Revises: 0004_teacher_voice_samples
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = "0005_production_platform"
down_revision = "0004_teacher_voice_samples"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in sa.inspect(bind).get_table_names()


def _extend_lesson_asset_enum() -> None:
    for value in ("audio", "image", "attachment"):
        op.execute(
            f"""
            DO $$ BEGIN
                ALTER TYPE lessonassettype ADD VALUE '{value}';
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )


def upgrade() -> None:
    # --- media_objects (must exist before lesson_assets.media_object_id) ---
    if not _table_exists("media_objects"):
        op.create_table(
            "media_objects",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("storage_provider", sa.String(length=32), server_default="local", nullable=False),
            sa.Column("storage_key", sa.String(length=1024), nullable=False),
            sa.Column("public_url", sa.String(length=2048), nullable=True),
            sa.Column("mime_type", sa.String(length=128), nullable=True),
            sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
            sa.Column("original_filename", sa.String(length=500), nullable=True),
            sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_media_objects_storage_provider", "media_objects", ["storage_provider"])
        op.create_index("ix_media_objects_storage_key", "media_objects", ["storage_key"])

    # --- audit_logs ---
    if not _table_exists("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("entity_type", sa.String(length=64), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=64), nullable=False),
            sa.Column("old_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("new_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
        op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
        op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # --- auth_sessions ---
    if not _table_exists("auth_sessions"):
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("refresh_token_hash", sa.String(length=255), nullable=False),
            sa.Column("device_name", sa.String(length=120), nullable=True),
            sa.Column("device_type", sa.String(length=32), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("refresh_token_hash"),
        )
        op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
        op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
        op.create_index("ix_auth_sessions_revoked_at", "auth_sessions", ["revoked_at"])

    # --- student_grade_reports ---
    if not _table_exists("student_grade_reports"):
        op.create_table(
            "student_grade_reports",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("course_id", sa.Integer(), nullable=False),
            sa.Column("average_score", sa.Float(), nullable=True),
            sa.Column("attendance_percentage", sa.Float(), nullable=True),
            sa.Column("completion_percentage", sa.Float(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("student_id", "course_id", name="uq_student_grade_report"),
        )
        op.create_index("ix_student_grade_reports_student_id", "student_grade_reports", ["student_id"])
        op.create_index("ix_student_grade_reports_course_id", "student_grade_reports", ["course_id"])

    # --- roles / user_roles ---
    if not _table_exists("roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("slug", sa.String(length=32), nullable=False),
            sa.Column("name_ar", sa.String(length=120), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
        )
        op.create_index("ix_roles_slug", "roles", ["slug"])

    if not _table_exists("user_roles"):
        op.create_table(
            "user_roles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        )
        op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
        op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    op.execute(
        """
        INSERT INTO roles (slug, name_ar) VALUES
            ('student', 'طالب'),
            ('teacher', 'معلم'),
            ('parent', 'ولي أمر'),
            ('admin', 'مدير'),
            ('support', 'دعم فني')
        ON CONFLICT (slug) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM users u
        JOIN roles r ON r.slug = u.role::text
        ON CONFLICT (user_id, role_id) DO NOTHING
        """
    )

    # --- analytics rollups ---
    if not _table_exists("course_analytics"):
        op.create_table(
            "course_analytics",
            sa.Column("course_id", sa.Integer(), nullable=False),
            sa.Column("student_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("completion_rate", sa.Float(), server_default="0", nullable=False),
            sa.Column("average_quiz_score", sa.Float(), nullable=True),
            sa.Column("active_students", sa.Integer(), server_default="0", nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("course_id"),
        )

    if not _table_exists("teacher_analytics"):
        op.create_table(
            "teacher_analytics",
            sa.Column("teacher_profile_id", sa.Integer(), nullable=False),
            sa.Column("total_students", sa.Integer(), server_default="0", nullable=False),
            sa.Column("total_courses", sa.Integer(), server_default="0", nullable=False),
            sa.Column("average_completion", sa.Float(), server_default="0", nullable=False),
            sa.Column("average_rating", sa.Float(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["teacher_profile_id"], ["teacher_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("teacher_profile_id"),
        )

    if not _table_exists("student_analytics"):
        op.create_table(
            "student_analytics",
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("completion_rate", sa.Float(), server_default="0", nullable=False),
            sa.Column("average_score", sa.Float(), nullable=True),
            sa.Column("total_study_hours", sa.Float(), server_default="0", nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("student_id"),
        )

    # --- ai_jobs ---
    if not _table_exists("ai_jobs"):
        op.create_table(
            "ai_jobs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("job_type", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
            sa.Column("lesson_id", sa.Integer(), nullable=True),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ai_jobs_job_type", "ai_jobs", ["job_type"])
        op.create_index("ix_ai_jobs_status", "ai_jobs", ["status"])
        op.create_index("ix_ai_jobs_lesson_id", "ai_jobs", ["lesson_id"])
        op.create_index("ix_ai_jobs_created_at", "ai_jobs", ["created_at"])

    # --- notifications: create if missing (legacy DBs), then payload + varchar type ---
    if not _table_exists("notifications"):
        op.execute(
            """
            DO $$ BEGIN
                CREATE TYPE notificationchannel AS ENUM ('in_app', 'email', 'sms', 'whatsapp');
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
        notification_channel = postgresql.ENUM(
            "in_app",
            "email",
            "sms",
            "whatsapp",
            name="notificationchannel",
            create_type=False,
        )
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column(
                "channel",
                notification_channel,
                server_default="in_app",
                nullable=False,
            ),
            sa.Column("type", sa.String(length=64), server_default="system", nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("data_json", sa.Text(), nullable=True),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
        op.create_index("ix_notifications_type", "notifications", ["type"])
        op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    else:
        op.execute(
            "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS payload JSONB"
        )
        bind = op.get_bind()
        row = bind.execute(
            text(
                """
                SELECT data_type, udt_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'notifications'
                  AND column_name = 'type'
                """
            )
        ).fetchone()
        if row and row.udt_name not in (None, "varchar", "character varying"):
            op.execute(
                """
                ALTER TABLE notifications
                ALTER COLUMN type TYPE VARCHAR(64)
                USING type::text
                """
            )

    # --- lesson_assets upgrade ---
    if _table_exists("lesson_assets"):
        _extend_lesson_asset_enum()
        op.execute("ALTER TABLE lesson_assets DROP CONSTRAINT IF EXISTS uq_lesson_asset_type")
        op.execute(
            "ALTER TABLE lesson_assets ADD COLUMN IF NOT EXISTS media_object_id INTEGER"
        )
        op.execute(
            "ALTER TABLE lesson_assets ADD COLUMN IF NOT EXISTS mime_type VARCHAR(128)"
        )
        op.execute(
            "ALTER TABLE lesson_assets ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT"
        )
        op.execute(
            """
            DO $$ BEGIN
                ALTER TABLE lesson_assets
                ADD CONSTRAINT fk_lesson_assets_media_object
                FOREIGN KEY (media_object_id) REFERENCES media_objects(id) ON DELETE SET NULL;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
        op.execute(
            """
            INSERT INTO media_objects (storage_provider, storage_key, public_url, original_filename)
            SELECT DISTINCT ON (la.storage_path)
                'local',
                la.storage_path,
                CASE
                    WHEN la.storage_path LIKE '/uploads/%' THEN la.storage_path
                    ELSE '/uploads/' || ltrim(la.storage_path, '/')
                END,
                la.original_filename
            FROM lesson_assets la
            WHERE la.storage_path IS NOT NULL AND la.storage_path <> ''
              AND NOT EXISTS (
                  SELECT 1 FROM media_objects m WHERE m.storage_key = la.storage_path
              )
            """
        )
        op.execute(
            """
            UPDATE lesson_assets la
            SET media_object_id = m.id
            FROM media_objects m
            WHERE m.storage_key = la.storage_path
              AND la.media_object_id IS NULL
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_lesson_assets_media_object_id ON lesson_assets(media_object_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_lesson_assets_sort_order ON lesson_assets(lesson_id, sort_order)"
        )

    # --- production indexes (idempotent) ---
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_courses_teacher_profile_id ON courses(teacher_profile_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_courses_subject_id ON courses(subject_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_courses_grade ON courses(grade)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lessons_course_id ON lessons(course_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lesson_assets_lesson_id ON lesson_assets(lesson_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_student_course_access_student_id ON student_course_access(student_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_student_course_access_course_id ON student_course_access(course_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_course_quiz_attempts_student_id ON course_quiz_attempts(student_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_course_quiz_attempts_quiz_id ON course_quiz_attempts(quiz_id)"
    )
    if _table_exists("payments"):
        op.execute("CREATE INDEX IF NOT EXISTS ix_payments_student_id ON payments(student_id)")
    if _table_exists("notifications"):
        op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id)")


def downgrade() -> None:
    # Indexes are left in place on downgrade to avoid breaking running systems.
    if _table_exists("lesson_assets"):
        op.execute(
            "ALTER TABLE lesson_assets DROP CONSTRAINT IF EXISTS fk_lesson_assets_media_object"
        )
        op.drop_column("lesson_assets", "file_size_bytes")
        op.drop_column("lesson_assets", "mime_type")
        op.drop_column("lesson_assets", "media_object_id")

    if _table_exists("notifications"):
        op.drop_column("notifications", "payload")

    for table in (
        "ai_jobs",
        "student_analytics",
        "teacher_analytics",
        "course_analytics",
        "user_roles",
        "roles",
        "student_grade_reports",
        "auth_sessions",
        "audit_logs",
        "media_objects",
    ):
        if _table_exists(table):
            op.drop_table(table)
