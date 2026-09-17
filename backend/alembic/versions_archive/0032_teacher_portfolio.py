"""Teacher portfolio: impact, philosophy, why-study, documents, pinned achievements."""

from alembic import op
import sqlalchemy as sa

revision = "0032_teacher_portfolio"
down_revision = "0031_teacher_profile_cv_sections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("teacher_profiles", sa.Column("impact_total_students", sa.Integer(), nullable=True))
    op.add_column("teacher_profiles", sa.Column("impact_grade12_students", sa.Integer(), nullable=True))
    op.add_column("teacher_profiles", sa.Column("impact_completed_subject", sa.Integer(), nullable=True))
    op.add_column("teacher_profiles", sa.Column("impact_excellent_grades", sa.Integer(), nullable=True))
    op.add_column("teacher_profiles", sa.Column("impact_years_teaching", sa.Integer(), nullable=True))
    op.add_column("teacher_profiles", sa.Column("philosophy_teaching_style", sa.Text(), nullable=True))
    op.add_column("teacher_profiles", sa.Column("philosophy_lesson_approach", sa.Text(), nullable=True))
    op.add_column("teacher_profiles", sa.Column("philosophy_exam_preparation", sa.Text(), nullable=True))

    op.add_column(
        "teacher_achievements",
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    op.create_table(
        "teacher_why_study_points",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("teacher_profile_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["teacher_profile_id"], ["teacher_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teacher_why_study_points_teacher_profile_id", "teacher_why_study_points", ["teacher_profile_id"])

    op.create_table(
        "teacher_professional_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("teacher_profile_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=32), server_default="certificate", nullable=False),
        sa.Column("file_url", sa.String(length=1024), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["teacher_profile_id"], ["teacher_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_teacher_professional_documents_teacher_profile_id",
        "teacher_professional_documents",
        ["teacher_profile_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_teacher_professional_documents_teacher_profile_id", table_name="teacher_professional_documents")
    op.drop_table("teacher_professional_documents")
    op.drop_index("ix_teacher_why_study_points_teacher_profile_id", table_name="teacher_why_study_points")
    op.drop_table("teacher_why_study_points")
    op.drop_column("teacher_achievements", "is_pinned")
    op.drop_column("teacher_profiles", "philosophy_exam_preparation")
    op.drop_column("teacher_profiles", "philosophy_lesson_approach")
    op.drop_column("teacher_profiles", "philosophy_teaching_style")
    op.drop_column("teacher_profiles", "impact_years_teaching")
    op.drop_column("teacher_profiles", "impact_excellent_grades")
    op.drop_column("teacher_profiles", "impact_completed_subject")
    op.drop_column("teacher_profiles", "impact_grade12_students")
    op.drop_column("teacher_profiles", "impact_total_students")
