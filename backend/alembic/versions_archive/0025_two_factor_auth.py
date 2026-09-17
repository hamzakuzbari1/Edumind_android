"""Two-factor authentication — user flags and login challenges."""

from alembic import op
import sqlalchemy as sa

revision = "0025_two_factor_auth"
down_revision = "0024_email_verification_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("two_factor_method", sa.String(length=16), nullable=True),
    )
    op.create_index("ix_users_two_factor_enabled", "users", ["two_factor_enabled"])

    op.create_table(
        "two_factor_challenges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=16), nullable=False),
        sa.Column("challenge_token_hash", sa.String(length=64), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resend_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_two_factor_challenges_user_id", "two_factor_challenges", ["user_id"])
    op.create_index("ix_two_factor_challenges_token_hash", "two_factor_challenges", ["challenge_token_hash"], unique=True)
    op.create_index("ix_two_factor_challenges_expires_at", "two_factor_challenges", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_two_factor_challenges_expires_at", table_name="two_factor_challenges")
    op.drop_index("ix_two_factor_challenges_token_hash", table_name="two_factor_challenges")
    op.drop_index("ix_two_factor_challenges_user_id", table_name="two_factor_challenges")
    op.drop_table("two_factor_challenges")
    op.drop_index("ix_users_two_factor_enabled", table_name="users")
    op.drop_column("users", "two_factor_method")
    op.drop_column("users", "two_factor_enabled")
