"""Dedupe course messaging threads and enforce one thread per (course, student)."""

from alembic import op
import sqlalchemy as sa

revision = "0018_course_thread_unique"
down_revision = "0017_course_messaging"
branch_labels = None
depends_on = None


def _dedupe_course_threads(connection) -> None:
    """Keep the best thread per (course_id, student_id); remove empty duplicates."""
    rows = connection.execute(
        sa.text(
            """
            SELECT course_id, student_id
            FROM conversation_threads
            WHERE course_id IS NOT NULL
            GROUP BY course_id, student_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()

    for course_id, student_id in rows:
        threads = connection.execute(
            sa.text(
                """
                SELECT t.id,
                       t.last_message_at,
                       (SELECT COUNT(*) FROM conversation_messages m WHERE m.thread_id = t.id) AS msg_count
                FROM conversation_threads t
                WHERE t.course_id = :course_id AND t.student_id = :student_id
                ORDER BY msg_count DESC,
                         t.last_message_at DESC NULLS LAST,
                         t.id ASC
                """
            ),
            {"course_id": course_id, "student_id": student_id},
        ).fetchall()
        keep_id = threads[0][0]
        for row in threads[1:]:
            tid, _, msg_count = row[0], row[1], row[2]
            if int(msg_count or 0) == 0:
                connection.execute(
                    sa.text("DELETE FROM conversation_threads WHERE id = :tid"),
                    {"tid": tid},
                )
            else:
                connection.execute(
                    sa.text(
                        "UPDATE conversation_threads SET course_id = NULL WHERE id = :tid"
                    ),
                    {"tid": tid},
                )


def upgrade() -> None:
    conn = op.get_bind()
    _dedupe_course_threads(conn)

    op.drop_index("ix_conversation_threads_course_student", table_name="conversation_threads")
    op.create_index(
        "uq_conversation_threads_course_student",
        "conversation_threads",
        ["course_id", "student_id"],
        unique=True,
        postgresql_where=sa.text("course_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_conversation_threads_course_student",
        table_name="conversation_threads",
        postgresql_where=sa.text("course_id IS NOT NULL"),
    )
    op.create_index(
        "ix_conversation_threads_course_student",
        "conversation_threads",
        ["course_id", "student_id"],
        unique=False,
    )
