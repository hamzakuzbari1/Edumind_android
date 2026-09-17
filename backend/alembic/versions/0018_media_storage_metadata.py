"""Add canonical storage metadata and media references.

Revision ID: 0018_media_storage_metadata
Revises: 0017_course_enrollment_entitlements
Create Date: 2026-09-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0018_media_storage_metadata"
down_revision = "0017_course_enrollment_entitlements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "media_objects",
        sa.Column("storage_bucket", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "media_objects",
        sa.Column("access_scope", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "media_objects",
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'ready'"),
            nullable=False,
        ),
    )
    op.add_column(
        "media_objects",
        sa.Column("checksum_sha256", sa.CHAR(length=64), nullable=True),
    )
    op.add_column(
        "media_objects",
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "media_objects",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "media_objects",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE media_objects
            SET access_scope = CASE
                WHEN public_url IS NOT NULL AND btrim(public_url) <> ''
                    THEN 'legacy_public'
                ELSE 'private'
            END
            WHERE access_scope IS NULL
            """
        )
    )
    op.alter_column(
        "media_objects",
        "access_scope",
        existing_type=sa.String(length=24),
        server_default=sa.text("'legacy_public'"),
        nullable=False,
    )

    missing_buckets = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM media_objects
            WHERE storage_provider = 'supabase'
              AND (storage_bucket IS NULL OR btrim(storage_bucket) = '')
            """
        )
    ).scalar_one()
    if missing_buckets:
        raise RuntimeError(
            "Supabase media rows require storage_bucket before A0.3 deployment: "
            f"count={missing_buckets}"
        )

    duplicate = bind.execute(
        sa.text(
            """
            SELECT storage_provider, storage_bucket, storage_key, count(*)
            FROM media_objects
            WHERE storage_bucket IS NOT NULL
              AND btrim(storage_bucket) <> ''
              AND btrim(storage_key) <> ''
              AND status <> 'deleted'
            GROUP BY storage_provider, storage_bucket, storage_key
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Duplicate canonical media storage identity blocks A0.3 deployment"
        )

    op.create_check_constraint(
        "ck_media_objects_access_scope",
        "media_objects",
        "access_scope IN ('private', 'public', 'legacy_public')",
    )
    op.create_check_constraint(
        "ck_media_objects_status",
        "media_objects",
        "status IN ('pending', 'ready', 'failed', 'deleted')",
    )
    op.create_check_constraint(
        "ck_media_objects_supabase_bucket",
        "media_objects",
        "storage_provider <> 'supabase' OR "
        "(storage_bucket IS NOT NULL AND btrim(storage_bucket) <> '')",
    )
    op.create_index(
        "uq_media_objects_canonical_storage_identity",
        "media_objects",
        ["storage_provider", "storage_bucket", "storage_key"],
        unique=True,
        postgresql_where=sa.text(
            "storage_bucket IS NOT NULL "
            "AND btrim(storage_bucket) <> '' "
            "AND btrim(storage_key) <> '' "
            "AND status <> 'deleted'"
        ),
    )

    op.add_column(
        "users",
        sa.Column("avatar_media_object_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_avatar_media_object_id_media_objects",
        "users",
        "media_objects",
        ["avatar_media_object_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "courses",
        sa.Column("thumbnail_media_object_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "courses",
        sa.Column("banner_media_object_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_courses_thumbnail_media_object_id_media_objects",
        "courses",
        "media_objects",
        ["thumbnail_media_object_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_courses_banner_media_object_id_media_objects",
        "courses",
        "media_objects",
        ["banner_media_object_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "teacher_professional_documents",
        sa.Column("media_object_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_teacher_professional_documents_media_object_id_media_objects",
        "teacher_professional_documents",
        "media_objects",
        ["media_object_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "teacher_voice_samples",
        sa.Column("source_media_object_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "teacher_voice_samples",
        sa.Column("preview_media_object_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_teacher_voice_samples_source_media_object_id_media_objects",
        "teacher_voice_samples",
        "media_objects",
        ["source_media_object_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_teacher_voice_samples_preview_media_object_id_media_objects",
        "teacher_voice_samples",
        "media_objects",
        ["preview_media_object_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "conversation_message_attachments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("media_object_id", sa.Integer(), nullable=False),
        sa.Column("attachment_kind", sa.String(length=24), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("voice_duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attachment_kind IN ('file', 'image', 'audio', 'video', 'document')",
            name="ck_conversation_message_attachments_kind",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["conversation_messages.id"],
            name="fk_conversation_message_attachments_message_id_messages",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["media_object_id"],
            ["media_objects.id"],
            name="fk_conversation_message_attachments_media_object",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_conversation_message_attachments"),
        sa.UniqueConstraint(
            "message_id",
            "media_object_id",
            name="uq_conversation_message_attachment_message_media",
        ),
    )
    op.create_index(
        "ix_conversation_message_attachments_message_order",
        "conversation_message_attachments",
        ["message_id", "sort_order", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_message_attachments_message_order",
        table_name="conversation_message_attachments",
    )
    op.drop_table("conversation_message_attachments")

    op.drop_constraint(
        "fk_teacher_voice_samples_preview_media_object_id_media_objects",
        "teacher_voice_samples",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_teacher_voice_samples_source_media_object_id_media_objects",
        "teacher_voice_samples",
        type_="foreignkey",
    )
    op.drop_column("teacher_voice_samples", "preview_media_object_id")
    op.drop_column("teacher_voice_samples", "source_media_object_id")

    op.drop_constraint(
        "fk_teacher_professional_documents_media_object_id_media_objects",
        "teacher_professional_documents",
        type_="foreignkey",
    )
    op.drop_column("teacher_professional_documents", "media_object_id")

    op.drop_constraint(
        "fk_courses_banner_media_object_id_media_objects",
        "courses",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_courses_thumbnail_media_object_id_media_objects",
        "courses",
        type_="foreignkey",
    )
    op.drop_column("courses", "banner_media_object_id")
    op.drop_column("courses", "thumbnail_media_object_id")

    op.drop_constraint(
        "fk_users_avatar_media_object_id_media_objects",
        "users",
        type_="foreignkey",
    )
    op.drop_column("users", "avatar_media_object_id")

    op.drop_index(
        "uq_media_objects_canonical_storage_identity",
        table_name="media_objects",
    )
    op.drop_constraint(
        "ck_media_objects_supabase_bucket",
        "media_objects",
        type_="check",
    )
    op.drop_constraint(
        "ck_media_objects_status",
        "media_objects",
        type_="check",
    )
    op.drop_constraint(
        "ck_media_objects_access_scope",
        "media_objects",
        type_="check",
    )
    op.drop_column("media_objects", "deleted_at")
    op.drop_column("media_objects", "updated_at")
    op.drop_column("media_objects", "metadata_json")
    op.drop_column("media_objects", "checksum_sha256")
    op.drop_column("media_objects", "status")
    op.drop_column("media_objects", "access_scope")
    op.drop_column("media_objects", "storage_bucket")
