"""AI token-usage ledger. New table only (additive, reversible).

Revision ID: 0058_ai_usage
Revises: 0057_progress_snapshots
"""

import sqlalchemy as sa
from alembic import op

revision = "0058_ai_usage"
down_revision = "0057_progress_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "language_ai_usage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("operation", sa.String(100), server_default="", nullable=False),
        sa.Column("model", sa.String(80), server_default="", nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_language_ai_usage_created_at", "language_ai_usage", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_language_ai_usage_created_at", table_name="language_ai_usage")
    op.drop_table("language_ai_usage")
