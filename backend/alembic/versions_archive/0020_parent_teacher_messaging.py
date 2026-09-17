"""Parent ↔ teacher messaging scope: parent_user_id + uniqueness."""

from alembic import op
import sqlalchemy as sa

revision = "0020_parent_teacher_messaging"
down_revision = "0019_teacher_thread_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversation_threads",
        sa.Column("parent_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversation_threads_parent_user_id",
        "conversation_threads",
        "users",
        ["parent_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_threads_parent_teacher_student_course",
        "conversation_threads",
        ["parent_user_id", "teacher_user_id", "student_id", "course_id"],
        unique=True,
        postgresql_where=sa.text(
            "parent_user_id IS NOT NULL AND teacher_user_id IS NOT NULL AND course_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_threads_parent_teacher_student_course",
        table_name="conversation_threads",
        postgresql_where=sa.text(
            "parent_user_id IS NOT NULL AND teacher_user_id IS NOT NULL AND course_id IS NOT NULL"
        ),
    )
    op.drop_constraint(
        "fk_conversation_threads_parent_user_id",
        "conversation_threads",
        type_="foreignkey",
    )
    op.drop_column("conversation_threads", "parent_user_id")
