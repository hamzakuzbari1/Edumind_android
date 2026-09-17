"""Student learning profile — long-term memory for lesson chat."""

from alembic import op
import sqlalchemy as sa

revision = "0040_student_learning_profile"
down_revision = "0039_teacher_ai_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "student_learning_profiles" in insp.get_table_names():
        return

    op.create_table(
        "student_learning_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("weak_topics_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("strong_topics_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("repeated_mistakes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("lesson_history_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("memory_summary", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_student_learning_profiles_user_id"),
    )
    op.create_index("ix_student_learning_profiles_user_id", "student_learning_profiles", ["user_id"])


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "student_learning_profiles" not in insp.get_table_names():
        return
    op.drop_index("ix_student_learning_profiles_user_id", table_name="student_learning_profiles")
    op.drop_table("student_learning_profiles")
