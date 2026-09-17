"""Add PostgreSQL enum lessonassettype and align lesson_assets.asset_type.

Revision ID: 0002_lesson_asset_enum
Revises: 0001_baseline
Create Date: 2026-05-29

The ORM uses native enum `lessonassettype` (video, pdf, homework).
Earlier schema patches created lesson_assets.asset_type as VARCHAR(32),
which causes asyncpg UndefinedObjectError on queries.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = "0002_lesson_asset_enum"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

LESSON_ASSET_ENUM = postgresql.ENUM(
    "video",
    "pdf",
    "homework",
    name="lessonassettype",
    create_type=False,
)


def _asset_type_udt(bind) -> str | None:
    row = bind.execute(
        text(
            """
            SELECT udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'lesson_assets'
              AND column_name = 'asset_type'
            """
        )
    ).fetchone()
    return row[0] if row else None


def _create_enum_type() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE lessonassettype AS ENUM ('video', 'pdf', 'homework');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )


def _backfill_lesson_assets() -> None:
    op.execute(
        """
        INSERT INTO lesson_assets (lesson_id, asset_type, storage_path, sort_order)
        SELECT id, 'video'::lessonassettype, video_url, 0 FROM lessons
        WHERE video_url IS NOT NULL AND video_url <> ''
        ON CONFLICT (lesson_id, asset_type) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO lesson_assets (lesson_id, asset_type, storage_path, sort_order)
        SELECT id, 'pdf'::lessonassettype, pdf_path, 1 FROM lessons
        WHERE pdf_path IS NOT NULL AND pdf_path <> ''
        ON CONFLICT (lesson_id, asset_type) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO lesson_assets (lesson_id, asset_type, storage_path, sort_order)
        SELECT id, 'homework'::lessonassettype, homework_path, 2 FROM lessons
        WHERE homework_path IS NOT NULL AND homework_path <> ''
        ON CONFLICT (lesson_id, asset_type) DO NOTHING
        """
    )


def upgrade() -> None:
    _create_enum_type()
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "lesson_assets" not in inspector.get_table_names():
        op.create_table(
            "lesson_assets",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("lesson_id", sa.Integer(), nullable=False),
            sa.Column("asset_type", LESSON_ASSET_ENUM, nullable=False),
            sa.Column("storage_path", sa.String(length=1024), nullable=False),
            sa.Column("original_filename", sa.String(length=500), nullable=True),
            sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("NOW()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("lesson_id", "asset_type", name="uq_lesson_asset_type"),
        )
        op.create_index("ix_lesson_assets_lesson_id", "lesson_assets", ["lesson_id"])
        op.create_index("ix_lesson_assets_asset_type", "lesson_assets", ["asset_type"])
        _backfill_lesson_assets()
        return

    udt = _asset_type_udt(bind)
    if udt != "lessonassettype":
        op.execute(
            "ALTER TABLE lesson_assets DROP CONSTRAINT IF EXISTS uq_lesson_asset_type"
        )
        op.execute(
            """
            ALTER TABLE lesson_assets
            ALTER COLUMN asset_type TYPE lessonassettype
            USING asset_type::text::lessonassettype
            """
        )
        op.execute(
            """
            ALTER TABLE lesson_assets
            ADD CONSTRAINT uq_lesson_asset_type UNIQUE (lesson_id, asset_type)
            """
        )

    _backfill_lesson_assets()


def downgrade() -> None:
    bind = op.get_bind()
    if "lesson_assets" not in sa.inspect(bind).get_table_names():
        op.execute("DROP TYPE IF EXISTS lessonassettype")
        return

    udt = _asset_type_udt(bind)
    if udt == "lessonassettype":
        op.execute(
            "ALTER TABLE lesson_assets DROP CONSTRAINT IF EXISTS uq_lesson_asset_type"
        )
        op.execute(
            """
            ALTER TABLE lesson_assets
            ALTER COLUMN asset_type TYPE VARCHAR(32)
            USING asset_type::text
            """
        )
        op.execute(
            """
            ALTER TABLE lesson_assets
            ADD CONSTRAINT uq_lesson_asset_type UNIQUE (lesson_id, asset_type)
            """
        )

    op.execute("DROP TYPE IF EXISTS lessonassettype")
