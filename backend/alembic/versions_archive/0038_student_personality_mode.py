"""Add personality_mode to student_profiles for lesson-chat tone."""

from alembic import op
import sqlalchemy as sa

revision = "0038_student_personality_mode"
down_revision = "0037_student_personalization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("student_profiles")}

    if "personality_mode" not in cols:
        op.add_column(
            "student_profiles",
            sa.Column(
                "personality_mode",
                sa.String(length=32),
                nullable=False,
                server_default="friendly_teacher",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("student_profiles")}

    if "personality_mode" in cols:
        op.drop_column("student_profiles", "personality_mode")
