"""Add student lesson-chat personalization questionnaire fields."""

from alembic import op
import sqlalchemy as sa

revision = "0037_student_personalization"
down_revision = "0036_speaking_conversation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("student_profiles")}

    if "age" not in cols:
        op.add_column(
            "student_profiles",
            sa.Column("age", sa.Integer(), nullable=True),
        )

    if "learning_style" not in cols:
        op.add_column(
            "student_profiles",
            sa.Column("learning_style", sa.String(length=32), nullable=False, server_default="theoretical"),
        )

    if "future_goal" not in cols:
        op.add_column(
            "student_profiles",
            sa.Column("future_goal", sa.String(length=32), nullable=False, server_default="undecided"),
        )

    if "preferred_explanation_style" not in cols:
        op.add_column(
            "student_profiles",
            sa.Column(
                "preferred_explanation_style",
                sa.String(length=32),
                nullable=False,
                server_default="normal",
            ),
        )

    if "hobbies_json" not in cols:
        op.add_column(
            "student_profiles",
            sa.Column("hobbies_json", sa.Text(), nullable=False, server_default="[]"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("student_profiles")}

    if "hobbies_json" in cols:
        op.drop_column("student_profiles", "hobbies_json")
    if "preferred_explanation_style" in cols:
        op.drop_column("student_profiles", "preferred_explanation_style")
    if "future_goal" in cols:
        op.drop_column("student_profiles", "future_goal")
    if "learning_style" in cols:
        op.drop_column("student_profiles", "learning_style")
    if "age" in cols:
        op.drop_column("student_profiles", "age")
