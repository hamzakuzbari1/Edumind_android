"""Parent-facing structured notes from teachers."""

from alembic import op
import sqlalchemy as sa

revision = "0013_student_parent_notes"
down_revision = "0012_teacher_student_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "student_parent_notes" not in insp.get_table_names():
        op.create_table(
            "student_parent_notes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("teacher_profile_id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("category", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["teacher_profile_id"], ["teacher_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_student_parent_notes_student_id", "student_parent_notes", ["student_id"])
        op.create_index("ix_student_parent_notes_teacher_profile_id", "student_parent_notes", ["teacher_profile_id"])
        op.create_index("ix_student_parent_notes_category", "student_parent_notes", ["category"])

    if "student_parent_note_reads" not in insp.get_table_names():
        op.create_table(
            "student_parent_note_reads",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("note_id", sa.Integer(), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["note_id"], ["student_parent_notes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["parent_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("note_id", "parent_id", name="uq_parent_note_read"),
        )
        op.create_index("ix_student_parent_note_reads_note_id", "student_parent_note_reads", ["note_id"])
        op.create_index("ix_student_parent_note_reads_parent_id", "student_parent_note_reads", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_student_parent_note_reads_parent_id", table_name="student_parent_note_reads")
    op.drop_index("ix_student_parent_note_reads_note_id", table_name="student_parent_note_reads")
    op.drop_table("student_parent_note_reads")
    op.drop_index("ix_student_parent_notes_category", table_name="student_parent_notes")
    op.drop_index("ix_student_parent_notes_teacher_profile_id", table_name="student_parent_notes")
    op.drop_index("ix_student_parent_notes_student_id", table_name="student_parent_notes")
    op.drop_table("student_parent_notes")
