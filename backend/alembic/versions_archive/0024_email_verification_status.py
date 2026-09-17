"""Add email_verified_at to users for account security center."""

from alembic import op
import sqlalchemy as sa

revision = "0024_email_verification_status"
down_revision = "0023_email_infrastructure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email_verified_at", "users", ["email_verified_at"])
    # Existing accounts treated as verified (grandfathered)
    op.execute(
        sa.text("UPDATE users SET email_verified_at = created_at WHERE email_verified_at IS NULL")
    )


def downgrade() -> None:
    op.drop_index("ix_users_email_verified_at", table_name="users")
    op.drop_column("users", "email_verified_at")
