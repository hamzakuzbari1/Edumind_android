"""Teacher AI identity and teaching profile for lesson chat."""

from alembic import op
import sqlalchemy as sa

revision = "0039_teacher_ai_identity"
down_revision = "0038_student_personality_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("teacher_profiles")}

    if "teacher_teaching_style" not in cols:
        op.add_column(
            "teacher_profiles",
            sa.Column(
                "teacher_teaching_style",
                sa.String(length=32),
                nullable=False,
                server_default="step_by_step",
            ),
        )
    if "teacher_tone" not in cols:
        op.add_column(
            "teacher_profiles",
            sa.Column(
                "teacher_tone",
                sa.String(length=32),
                nullable=False,
                server_default="balanced",
            ),
        )
    if "teacher_question_style" not in cols:
        op.add_column(
            "teacher_profiles",
            sa.Column(
                "teacher_question_style",
                sa.String(length=32),
                nullable=False,
                server_default="mixed",
            ),
        )
    if "teacher_motivation_level" not in cols:
        op.add_column(
            "teacher_profiles",
            sa.Column(
                "teacher_motivation_level",
                sa.String(length=32),
                nullable=False,
                server_default="medium",
            ),
        )
    if "teacher_display_name" not in cols:
        op.add_column(
            "teacher_profiles",
            sa.Column("teacher_display_name", sa.String(length=255), nullable=True),
        )
    if "teacher_signature_phrase" not in cols:
        op.add_column(
            "teacher_profiles",
            sa.Column("teacher_signature_phrase", sa.String(length=500), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("teacher_profiles")}

    for name in (
        "teacher_signature_phrase",
        "teacher_display_name",
        "teacher_motivation_level",
        "teacher_question_style",
        "teacher_tone",
        "teacher_teaching_style",
    ):
        if name in cols:
            op.drop_column("teacher_profiles", name)
