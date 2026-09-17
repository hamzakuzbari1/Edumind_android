"""Email infrastructure: verification and password-reset tokens."""

from alembic import op
import sqlalchemy as sa

revision = "0023_email_infrastructure"
down_revision = "0022_gamification_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(32), server_default="verification", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_email_tokens_token_hash"),
    )
    op.create_index("ix_email_tokens_user_id", "email_tokens", ["user_id"])
    op.create_index("ix_email_tokens_purpose", "email_tokens", ["purpose"])
    op.create_index("ix_email_tokens_expires_at", "email_tokens", ["expires_at"])
    op.create_index("ix_email_tokens_used_at", "email_tokens", ["used_at"])


def downgrade() -> None:
    op.drop_index("ix_email_tokens_used_at", table_name="email_tokens")
    op.drop_index("ix_email_tokens_expires_at", table_name="email_tokens")
    op.drop_index("ix_email_tokens_purpose", table_name="email_tokens")
    op.drop_index("ix_email_tokens_user_id", table_name="email_tokens")
    op.drop_table("email_tokens")
