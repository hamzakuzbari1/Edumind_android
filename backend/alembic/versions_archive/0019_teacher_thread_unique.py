"""Add teacher_user_id + enforce (teacher, student, course) uniqueness; merge duplicates."""

from alembic import op
import sqlalchemy as sa

revision = "0019_teacher_thread_unique"
down_revision = "0018_course_thread_unique"
branch_labels = None
depends_on = None


def _backfill_teacher_user_id(connection) -> None:
    connection.execute(
        sa.text(
            """
            UPDATE conversation_threads AS t
            SET teacher_user_id = cp.user_id
            FROM conversation_participants AS cp
            WHERE cp.thread_id = t.id
              AND cp.role = 'teacher'
              AND t.teacher_user_id IS NULL
            """
        )
    )


def _merge_duplicates(connection) -> None:
    """Keep thread with most messages; reassign messages; delete empty duplicates."""
    rows = connection.execute(
        sa.text(
            """
            SELECT
                t.id AS thread_id,
                t.student_id,
                t.course_id,
                t.teacher_user_id,
                (SELECT COUNT(*) FROM conversation_messages m WHERE m.thread_id = t.id) AS msg_count,
                t.last_message_at,
                t.created_at
            FROM conversation_threads t
            WHERE t.teacher_user_id IS NOT NULL
            ORDER BY t.student_id, t.teacher_user_id, t.course_id NULLS FIRST, t.id
            """
        )
    ).fetchall()

    from collections import defaultdict

    # Group by (teacher, student, course_id or LEGACY)
    groups: dict[tuple, list] = defaultdict(list)
    for row in rows:
        cid = row.course_id if row.course_id is not None else -1
        groups[(row.teacher_user_id, row.student_id, cid)].append(row)

    # Also merge legacy (-1) with each real course_id for same teacher+student
    by_pair: dict[tuple, list] = defaultdict(list)
    for row in rows:
        by_pair[(row.teacher_user_id, row.student_id)].append(row)

    def pick_winner(items: list) -> object:
        return max(
            items,
            key=lambda r: (
                int(r.msg_count or 0),
                r.last_message_at or r.created_at,
                -r.thread_id,
            ),
        )

    merged_ids: set[int] = set()

    for (_teacher, _student, _cid), items in groups.items():
        if len(items) < 2:
            continue
        winner = pick_winner(items)
        for row in items:
            if row.thread_id == winner.thread_id:
                continue
            if row.thread_id in merged_ids:
                continue
            connection.execute(
                sa.text(
                    "UPDATE conversation_messages SET thread_id = :w WHERE thread_id = :l"
                ),
                {"w": winner.thread_id, "l": row.thread_id},
            )
            connection.execute(
                sa.text(
                    "DELETE FROM conversation_participants WHERE thread_id = :l"
                ),
                {"l": row.thread_id},
            )
            connection.execute(
                sa.text("DELETE FROM conversation_threads WHERE id = :l"),
                {"l": row.thread_id},
            )
            merged_ids.add(row.thread_id)

    for (_teacher, _student), items in by_pair.items():
        legacy = [r for r in items if r.course_id is None]
        scoped = [r for r in items if r.course_id is not None]
        if not legacy or not scoped:
            continue
        for course_row in scoped:
            pool = legacy + [course_row]
            if len(pool) < 2:
                continue
            winner = pick_winner(pool)
            for row in pool:
                if row.thread_id == winner.thread_id or row.thread_id in merged_ids:
                    continue
                connection.execute(
                    sa.text(
                        "UPDATE conversation_messages SET thread_id = :w WHERE thread_id = :l"
                    ),
                    {"w": winner.thread_id, "l": row.thread_id},
                )
                connection.execute(
                    sa.text(
                        "DELETE FROM conversation_participants WHERE thread_id = :l"
                    ),
                    {"l": row.thread_id},
                )
                connection.execute(
                    sa.text("DELETE FROM conversation_threads WHERE id = :l"),
                    {"l": row.thread_id},
                )
                merged_ids.add(row.thread_id)
            connection.execute(
                sa.text(
                    """
                    UPDATE conversation_threads
                    SET course_id = :cid, teacher_user_id = :tid
                    WHERE id = :wid
                    """
                ),
                {
                    "cid": course_row.course_id,
                    "tid": _teacher,
                    "wid": winner.thread_id,
                },
            )


def upgrade() -> None:
    op.add_column(
        "conversation_threads",
        sa.Column("teacher_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversation_threads_teacher_user_id",
        "conversation_threads",
        "users",
        ["teacher_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    conn = op.get_bind()
    _backfill_teacher_user_id(conn)
    _merge_duplicates(conn)

    op.drop_index(
        "uq_conversation_threads_course_student",
        table_name="conversation_threads",
        postgresql_where=sa.text("course_id IS NOT NULL"),
    )
    op.create_index(
        "uq_threads_teacher_student_course",
        "conversation_threads",
        ["teacher_user_id", "student_id", "course_id"],
        unique=True,
        postgresql_where=sa.text("course_id IS NOT NULL AND teacher_user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_threads_teacher_student_legacy",
        "conversation_threads",
        ["teacher_user_id", "student_id"],
        unique=True,
        postgresql_where=sa.text(
            "course_id IS NULL AND teacher_user_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_threads_teacher_student_legacy",
        table_name="conversation_threads",
        postgresql_where=sa.text("course_id IS NULL AND teacher_user_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_threads_teacher_student_course",
        table_name="conversation_threads",
        postgresql_where=sa.text("course_id IS NOT NULL AND teacher_user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_conversation_threads_course_student",
        "conversation_threads",
        ["course_id", "student_id"],
        unique=True,
        postgresql_where=sa.text("course_id IS NOT NULL"),
    )
    op.drop_constraint(
        "fk_conversation_threads_teacher_user_id",
        "conversation_threads",
        type_="foreignkey",
    )
    op.drop_column("conversation_threads", "teacher_user_id")
