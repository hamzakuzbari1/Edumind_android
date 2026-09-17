"""Parent note threads: status, priority, replies."""

from alembic import op
import sqlalchemy as sa

revision = "0014_parent_note_threads"
down_revision = "0013_student_parent_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tables = insp.get_table_names()

    if "student_parent_notes" in tables:
        cols = {c["name"] for c in insp.get_columns("student_parent_notes")}
        if "status" not in cols:
            op.add_column(
                "student_parent_notes",
                sa.Column("status", sa.String(length=16), nullable=False, server_default="new"),
            )
            op.create_index("ix_student_parent_notes_status", "student_parent_notes", ["status"])
        if "priority" not in cols:
            op.add_column(
                "student_parent_notes",
                sa.Column("priority", sa.String(length=16), nullable=False, server_default="medium"),
            )
            op.create_index("ix_student_parent_notes_priority", "student_parent_notes", ["priority"])
        if "closed_at" not in cols:
            op.add_column(
                "student_parent_notes",
                sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            )
        if "closed_by_user_id" not in cols:
            op.add_column(
                "student_parent_notes",
                sa.Column("closed_by_user_id", sa.Integer(), nullable=True),
            )
            op.create_foreign_key(
                "fk_student_parent_notes_closed_by",
                "student_parent_notes",
                "users",
                ["closed_by_user_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if "student_parent_note_replies" not in tables:
        op.create_table(
            "student_parent_note_replies",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("note_id", sa.Integer(), nullable=False),
            sa.Column("author_id", sa.Integer(), nullable=False),
            sa.Column("author_role", sa.String(length=16), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["note_id"], ["student_parent_notes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_student_parent_note_replies_note_id", "student_parent_note_replies", ["note_id"])
        op.create_index("ix_student_parent_note_replies_author_id", "student_parent_note_replies", ["author_id"])


def downgrade() -> None:
    op.drop_index("ix_student_parent_note_replies_author_id", table_name="student_parent_note_replies")
    op.drop_index("ix_student_parent_note_replies_note_id", table_name="student_parent_note_replies")
    op.drop_table("student_parent_note_replies")
    op.drop_constraint("fk_student_parent_notes_closed_by", "student_parent_notes", type_="foreignkey")
    op.drop_index("ix_student_parent_notes_priority", table_name="student_parent_notes")
    op.drop_index("ix_student_parent_notes_status", table_name="student_parent_notes")
    op.drop_column("student_parent_notes", "closed_by_user_id")
    op.drop_column("student_parent_notes", "closed_at")
    op.drop_column("student_parent_notes", "priority")
    op.drop_column("student_parent_notes", "status")
