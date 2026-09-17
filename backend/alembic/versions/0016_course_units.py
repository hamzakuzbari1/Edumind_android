"""Add canonical course units and assign existing course lessons.

Revision ID: 0016_course_units
Revises: 0015_merge_vocabulary_fixed_bank
Create Date: 2026-09-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0016_course_units"
down_revision = "0015_merge_vocabulary_fixed_bank"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "course_units",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_visible", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_course_units_course_id_courses",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_course_units"),
        sa.UniqueConstraint("course_id", "id", name="uq_course_units_course_id_id"),
    )
    op.create_index(
        "ix_course_units_course_sort_id",
        "course_units",
        ["course_id", "sort_order", "id"],
        unique=False,
    )

    op.add_column("lessons", sa.Column("unit_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_lessons_course_unit",
        "lessons",
        "course_units",
        ["course_id", "unit_id"],
        ["course_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_lessons_unit_requires_course",
        "lessons",
        "unit_id IS NULL OR course_id IS NOT NULL",
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO course_units (
                course_id, title, description, sort_order, is_visible, created_at, updated_at
            )
            SELECT DISTINCT
                lessons.course_id, :title, NULL, 0, true, now(), now()
            FROM lessons
            WHERE lessons.course_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM course_units
                  WHERE course_units.course_id = lessons.course_id
              )
            """
        ),
        {"title": "عام"},
    )
    bind.execute(
        sa.text(
            """
            UPDATE lessons
            SET unit_id = course_units.id
            FROM course_units
            WHERE lessons.course_id = course_units.course_id
              AND lessons.course_id IS NOT NULL
              AND lessons.unit_id IS NULL
            """
        )
    )

    missing_unit_count = bind.execute(
        sa.text("SELECT count(*) FROM lessons WHERE course_id IS NOT NULL AND unit_id IS NULL")
    ).scalar_one()
    mismatched_unit_count = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM lessons
            JOIN course_units ON course_units.id = lessons.unit_id
            WHERE lessons.course_id IS DISTINCT FROM course_units.course_id
            """
        )
    ).scalar_one()
    if missing_unit_count or mismatched_unit_count:
        raise RuntimeError(
            "Course unit backfill validation failed: "
            f"missing={missing_unit_count}, mismatched={mismatched_unit_count}"
        )


def downgrade() -> None:
    op.drop_constraint("ck_lessons_unit_requires_course", "lessons", type_="check")
    op.drop_constraint("fk_lessons_course_unit", "lessons", type_="foreignkey")
    op.drop_column("lessons", "unit_id")
    op.drop_index("ix_course_units_course_sort_id", table_name="course_units")
    op.drop_table("course_units")
