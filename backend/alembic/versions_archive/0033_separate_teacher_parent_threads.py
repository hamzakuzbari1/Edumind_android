"""Separate teacher_parent threads from teacher_student; scope unique indexes by type."""

from alembic import op
import sqlalchemy as sa

revision = "0033_teacher_parent_threads"
down_revision = "0032_teacher_portfolio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Revert student threads that were upgraded to include parents (shared history bug).
    conn.execute(
        sa.text(
            """
            DELETE FROM conversation_participants cp
            USING conversation_threads t
            WHERE cp.thread_id = t.id
              AND cp.role = 'parent'
              AND t.thread_type IN ('teacher_student_parent', 'teacher_student')
              AND EXISTS (
                  SELECT 1 FROM conversation_participants sp
                  WHERE sp.thread_id = t.id AND sp.role = 'student'
              )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE conversation_threads
            SET thread_type = 'teacher_student',
                include_parent = false,
                parent_user_id = NULL
            WHERE thread_type = 'teacher_student_parent'
               OR (include_parent = true AND parent_user_id IS NOT NULL)
            """
        )
    )

    op.drop_index(
        "uq_threads_teacher_student_course",
        table_name="conversation_threads",
        postgresql_where=sa.text("course_id IS NOT NULL AND teacher_user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_threads_teacher_student_course",
        "conversation_threads",
        ["teacher_user_id", "student_id", "course_id"],
        unique=True,
        postgresql_where=sa.text(
            "course_id IS NOT NULL AND teacher_user_id IS NOT NULL "
            "AND thread_type = 'teacher_student'"
        ),
    )

    op.drop_index(
        "uq_threads_parent_teacher_student_course",
        table_name="conversation_threads",
        postgresql_where=sa.text(
            "parent_user_id IS NOT NULL AND teacher_user_id IS NOT NULL AND course_id IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_threads_parent_teacher_student_course",
        "conversation_threads",
        ["parent_user_id", "teacher_user_id", "student_id", "course_id"],
        unique=True,
        postgresql_where=sa.text(
            "parent_user_id IS NOT NULL AND teacher_user_id IS NOT NULL "
            "AND course_id IS NOT NULL AND thread_type = 'teacher_parent'"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_threads_parent_teacher_student_course",
        table_name="conversation_threads",
        postgresql_where=sa.text(
            "parent_user_id IS NOT NULL AND teacher_user_id IS NOT NULL "
            "AND course_id IS NOT NULL AND thread_type = 'teacher_parent'"
        ),
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

    op.drop_index(
        "uq_threads_teacher_student_course",
        table_name="conversation_threads",
        postgresql_where=sa.text(
            "course_id IS NOT NULL AND teacher_user_id IS NOT NULL "
            "AND thread_type = 'teacher_student'"
        ),
    )
    op.create_index(
        "uq_threads_teacher_student_course",
        "conversation_threads",
        ["teacher_user_id", "student_id", "course_id"],
        unique=True,
        postgresql_where=sa.text("course_id IS NOT NULL AND teacher_user_id IS NOT NULL"),
    )
