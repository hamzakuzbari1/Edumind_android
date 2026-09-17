"""Add recent_scores_json to language_skill_level_state when missing.

Revision ID: 0043_add_recent_scores_json
Revises: 0042_adaptive_difficulty

Safe for legacy mixed databases: table may pre-exist without this column.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0043_add_recent_scores_json"
down_revision = "0042_adaptive_difficulty"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "language_skill_level_state" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("language_skill_level_state")}
    if "recent_scores_json" in cols:
        return

    op.add_column(
        "language_skill_level_state",
        sa.Column(
            "recent_scores_json",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "language_skill_level_state" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("language_skill_level_state")}
    if "recent_scores_json" not in cols:
        return

    op.drop_column("language_skill_level_state", "recent_scores_json")
