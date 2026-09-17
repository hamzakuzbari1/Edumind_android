"""Language analytics achievements, scenario progress, and statistics rollup.

Revision ID: 0044_language_analytics_achievements
Revises: 0043_add_recent_scores_json
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0044_language_analytics_achievements"
down_revision = "0043_add_recent_scores_json"
branch_labels = None
depends_on = None


def _column_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c LIMIT 1"
        ),
        {"t": table, "c": column},
    ).fetchone()
    return row is not None


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t LIMIT 1"),
        {"t": table},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _table_exists(conn, "language_student_achievements"):
        op.create_table(
            "language_student_achievements",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("language_id", sa.Integer(), nullable=False),
            sa.Column("achievement_key", sa.String(length=64), nullable=False),
            sa.Column("unlocked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["language_id"], ["languages.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "student_id",
                "language_id",
                "achievement_key",
                name="uq_language_student_achievement",
            ),
        )
        op.create_index(
            "ix_language_student_achievements_student",
            "language_student_achievements",
            ["student_id", "language_id"],
        )

    if not _table_exists(conn, "language_scenario_progress"):
        op.create_table(
            "language_scenario_progress",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("student_id", sa.Integer(), nullable=False),
            sa.Column("language_id", sa.Integer(), nullable=False),
            sa.Column("scenario_key", sa.String(length=64), nullable=False),
            sa.Column("scenario_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=16), server_default="not_started", nullable=False),
            sa.Column("completion_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("best_score", sa.Integer(), server_default="0", nullable=False),
            sa.Column("best_scores_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("last_played_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("first_completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["language_id"], ["languages.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "student_id",
                "language_id",
                "scenario_key",
                name="uq_language_scenario_progress_key",
            ),
        )
        op.create_index(
            "ix_language_scenario_progress_student",
            "language_scenario_progress",
            ["student_id", "language_id"],
        )

    if not _column_exists(conn, "language_analytics", "statistics_json"):
        op.add_column(
            "language_analytics",
            sa.Column("statistics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "language_analytics", "statistics_json"):
        op.drop_column("language_analytics", "statistics_json")
    if _table_exists(conn, "language_scenario_progress"):
        op.drop_table("language_scenario_progress")
    if _table_exists(conn, "language_student_achievements"):
        op.drop_table("language_student_achievements")
