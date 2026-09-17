"""Add status column to routine_slots for session completion tracking."""

from alembic import op
import sqlalchemy as sa

revision = "0009_routine_slot_status"
down_revision = "0008_language_learning_phase1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "routine_slots",
        sa.Column("status", sa.String(16), nullable=False, server_default="planned"),
    )


def downgrade() -> None:
    op.drop_column("routine_slots", "status")
