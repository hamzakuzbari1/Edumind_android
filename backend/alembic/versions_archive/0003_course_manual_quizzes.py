"""Teacher manual course quizzes (questions, attempts, answers).

Revision ID: 0003_course_manual_quizzes
Revises: 0002_lesson_asset_enum

Idempotent: tables may already exist from legacy schema_patch on pre-Alembic databases.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_course_manual_quizzes"
down_revision = "0002_lesson_asset_enum"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    if not _table_exists("course_quizzes"):
        op.create_table(
            "course_quizzes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("course_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("duration_minutes", sa.Integer(), nullable=True),
            sa.Column("passing_score_percent", sa.Integer(), server_default="60", nullable=False),
            sa.Column("is_published", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_course_quizzes_course_id ON course_quizzes(course_id)")

    if not _table_exists("course_quiz_questions"):
        op.create_table(
            "course_quiz_questions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("quiz_id", sa.Integer(), nullable=False),
            sa.Column("question_type", sa.String(length=32), nullable=False),
            sa.Column("question_text", sa.Text(), nullable=False),
            sa.Column("options_json", sa.Text(), nullable=True),
            sa.Column("correct_answer_json", sa.Text(), nullable=True),
            sa.Column("points", sa.Integer(), server_default="1", nullable=False),
            sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
            sa.Column("requires_manual_grading", sa.Boolean(), server_default="false", nullable=False),
            sa.ForeignKeyConstraint(["quiz_id"], ["course_quizzes.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_course_quiz_questions_quiz_id ON course_quiz_questions(quiz_id)"
    )

    if not _table_exists("course_quiz_attempts"):
        op.create_table(
            "course_quiz_attempts",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("quiz_id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="in_progress", nullable=False),
            sa.Column("score", sa.Float(), server_default="0", nullable=False),
            sa.Column("max_score", sa.Float(), server_default="0", nullable=False),
            sa.Column("percent", sa.Float(), nullable=True),
            sa.Column("passed", sa.Boolean(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["quiz_id"], ["course_quizzes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("quiz_id", "student_id", name="uq_course_quiz_attempt"),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_course_quiz_attempts_quiz_id ON course_quiz_attempts(quiz_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_course_quiz_attempts_student_id ON course_quiz_attempts(student_id)"
    )

    if not _table_exists("course_quiz_answers"):
        op.create_table(
            "course_quiz_answers",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("attempt_id", sa.Integer(), nullable=False),
            sa.Column("question_id", sa.Integer(), nullable=False),
            sa.Column("answer_json", sa.Text(), nullable=True),
            sa.Column("points_earned", sa.Float(), nullable=True),
            sa.Column("is_correct", sa.Boolean(), nullable=True),
            sa.Column("teacher_feedback", sa.Text(), nullable=True),
            sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("graded_by_user_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["attempt_id"], ["course_quiz_attempts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["question_id"], ["course_quiz_questions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["graded_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("attempt_id", "question_id", name="uq_course_quiz_answer"),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_course_quiz_answers_attempt_id ON course_quiz_answers(attempt_id)"
    )


def downgrade() -> None:
    op.drop_table("course_quiz_answers")
    op.drop_table("course_quiz_attempts")
    op.drop_table("course_quiz_questions")
    op.drop_table("course_quizzes")
