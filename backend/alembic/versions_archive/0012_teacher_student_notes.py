"""Teacher private notes about students."""

from alembic import op
import sqlalchemy as sa

revision = "0012_teacher_student_notes"
down_revision = "0011_language_c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "teacher_student_notes" not in insp.get_table_names():
        op.create_table(
            "teacher_student_notes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("teacher_profile_id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("note_text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["teacher_profile_id"], ["teacher_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_teacher_student_notes_teacher_profile_id",
            "teacher_student_notes",
            ["teacher_profile_id"],
        )
        op.create_index(
            "ix_teacher_student_notes_student_id",
            "teacher_student_notes",
            ["student_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_teacher_student_notes_student_id", table_name="teacher_student_notes")
    op.drop_index("ix_teacher_student_notes_teacher_profile_id", table_name="teacher_student_notes")
    op.drop_table("teacher_student_notes")
