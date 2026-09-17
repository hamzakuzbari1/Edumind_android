"""Add cached AI-curated lesson insights (takeaways + concepts)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0052_lesson_insights_json"
down_revision = "0051_fix_lesson_content_type"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column in {col["name"] for col in insp.get_columns(table)}


def upgrade() -> None:
    if not _column_exists("lessons", "insights_json"):
        op.add_column("lessons", sa.Column("insights_json", JSONB, nullable=True))


def downgrade() -> None:
    if _column_exists("lessons", "insights_json"):
        op.drop_column("lessons", "insights_json")
