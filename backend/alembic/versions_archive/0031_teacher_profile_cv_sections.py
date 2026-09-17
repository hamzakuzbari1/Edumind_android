"""Teacher profile CV sections: qualifications, experience, achievements."""

from alembic import op
import sqlalchemy as sa

revision = "0031_teacher_profile_cv_sections"
down_revision = "0030_parent_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teacher_qualifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("teacher_profile_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("institution", sa.String(length=255), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["teacher_profile_id"], ["teacher_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teacher_qualifications_teacher_profile_id", "teacher_qualifications", ["teacher_profile_id"])

    op.create_table(
        "teacher_teaching_experiences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("teacher_profile_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("organization", sa.String(length=255), nullable=True),
        sa.Column("year_from", sa.Integer(), nullable=True),
        sa.Column("year_to", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["teacher_profile_id"], ["teacher_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_teacher_teaching_experiences_teacher_profile_id",
        "teacher_teaching_experiences",
        ["teacher_profile_id"],
    )

    op.create_table(
        "teacher_achievements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("teacher_profile_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["teacher_profile_id"], ["teacher_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teacher_achievements_teacher_profile_id", "teacher_achievements", ["teacher_profile_id"])


def downgrade() -> None:
    op.drop_index("ix_teacher_achievements_teacher_profile_id", table_name="teacher_achievements")
    op.drop_table("teacher_achievements")
    op.drop_index("ix_teacher_teaching_experiences_teacher_profile_id", table_name="teacher_teaching_experiences")
    op.drop_table("teacher_teaching_experiences")
    op.drop_index("ix_teacher_qualifications_teacher_profile_id", table_name="teacher_qualifications")
    op.drop_table("teacher_qualifications")
