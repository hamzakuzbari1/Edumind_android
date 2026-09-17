"""Phase 6B.3: course-linked messaging threads."""

from alembic import op
import sqlalchemy as sa

revision = "0017_course_messaging"
down_revision = "0016_smart_messaging"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversation_threads",
        sa.Column("course_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "conversation_threads",
        sa.Column(
            "include_parent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_foreign_key(
        "fk_conversation_threads_course_id",
        "conversation_threads",
        "courses",
        ["course_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_conversation_threads_course_student",
        "conversation_threads",
        ["course_id", "student_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_threads_course_student", table_name="conversation_threads")
    op.drop_constraint("fk_conversation_threads_course_id", "conversation_threads", type_="foreignkey")
    op.drop_column("conversation_threads", "include_parent")
    op.drop_column("conversation_threads", "course_id")
