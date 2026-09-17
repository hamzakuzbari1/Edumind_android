"""Add persistent, versioned teacher voice consent records.

Revision ID: 0019_teacher_voice_consent
Revises: 0018_media_storage_metadata
Create Date: 2026-09-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0019_teacher_voice_consent"
down_revision = "0018_media_storage_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voice_consent_policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("policy_key", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("policy_text", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("policy_uri", sa.Text(), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_voice_consent_policies"),
        sa.UniqueConstraint(
            "policy_key",
            "version",
            name="uq_voice_consent_policies_key_version",
        ),
    )
    op.create_index(
        "ix_voice_consent_policies_key_effective",
        "voice_consent_policies",
        ["policy_key", "effective_at"],
    )

    op.create_table(
        "teacher_voice_consents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("teacher_profile_id", sa.Integer(), nullable=False),
        sa.Column("consenting_user_id", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.Integer(), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column(
            "evidence_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('granted', 'revoked')",
            name="ck_teacher_voice_consents_status",
        ),
        sa.CheckConstraint(
            "source IN ('web', 'android', 'admin_recorded', 'import')",
            name="ck_teacher_voice_consents_source",
        ),
        sa.CheckConstraint(
            "(status = 'granted' AND revoked_at IS NULL) OR "
            "(status = 'revoked' AND revoked_at IS NOT NULL)",
            name="ck_teacher_voice_consents_state",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_profile_id"],
            ["teacher_profiles.id"],
            name="fk_teacher_voice_consents_teacher_profile",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["consenting_user_id"],
            ["users.id"],
            name="fk_teacher_voice_consents_consenting_user",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["voice_consent_policies.id"],
            name="fk_teacher_voice_consents_policy",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_user_id"],
            ["users.id"],
            name="fk_teacher_voice_consents_revoked_by_user",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_teacher_voice_consents"),
    )
    op.create_index(
        "ix_teacher_voice_consents_teacher_profile_id",
        "teacher_voice_consents",
        ["teacher_profile_id"],
    )
    op.create_index(
        "ix_teacher_voice_consents_consenting_user_id",
        "teacher_voice_consents",
        ["consenting_user_id"],
    )
    op.create_index(
        "ix_teacher_voice_consents_policy_id",
        "teacher_voice_consents",
        ["policy_id"],
    )
    op.create_index(
        "ix_teacher_voice_consents_status",
        "teacher_voice_consents",
        ["status"],
    )
    op.create_index(
        "uq_teacher_voice_consents_active_teacher_profile",
        "teacher_voice_consents",
        ["teacher_profile_id"],
        unique=True,
        postgresql_where=sa.text("status = 'granted'"),
    )

    op.add_column(
        "teacher_voice_samples",
        sa.Column("voice_consent_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_teacher_voice_samples_voice_consent",
        "teacher_voice_samples",
        "teacher_voice_consents",
        ["voice_consent_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_teacher_voice_samples_voice_consent",
        "teacher_voice_samples",
        type_="foreignkey",
    )
    op.drop_column("teacher_voice_samples", "voice_consent_id")

    op.drop_index(
        "uq_teacher_voice_consents_active_teacher_profile",
        table_name="teacher_voice_consents",
    )
    op.drop_index(
        "ix_teacher_voice_consents_status",
        table_name="teacher_voice_consents",
    )
    op.drop_index(
        "ix_teacher_voice_consents_policy_id",
        table_name="teacher_voice_consents",
    )
    op.drop_index(
        "ix_teacher_voice_consents_consenting_user_id",
        table_name="teacher_voice_consents",
    )
    op.drop_index(
        "ix_teacher_voice_consents_teacher_profile_id",
        table_name="teacher_voice_consents",
    )
    op.drop_table("teacher_voice_consents")

    op.drop_index(
        "ix_voice_consent_policies_key_effective",
        table_name="voice_consent_policies",
    )
    op.drop_table("voice_consent_policies")
