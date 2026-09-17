"""Phase 6B: smart messaging — pin/archive, attachments, voice, soft delete."""

from alembic import op
import sqlalchemy as sa

revision = "0016_smart_messaging"
down_revision = "0015_internal_messaging"
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if table not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    if column.name not in existing:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing(
        "conversation_participants",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    _add_column_if_missing(
        "conversation_participants",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    _add_column_if_missing(
        "conversation_messages",
        sa.Column("message_kind", sa.String(length=24), nullable=False, server_default="text"),
    )
    _add_column_if_missing(
        "conversation_messages",
        sa.Column("attachment_url", sa.String(length=512), nullable=True),
    )
    _add_column_if_missing(
        "conversation_messages",
        sa.Column("attachment_name", sa.String(length=255), nullable=True),
    )
    _add_column_if_missing(
        "conversation_messages",
        sa.Column("attachment_mime", sa.String(length=128), nullable=True),
    )
    _add_column_if_missing(
        "conversation_messages",
        sa.Column("voice_duration_ms", sa.Integer(), nullable=True),
    )
    _add_column_if_missing(
        "conversation_messages",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    for table, col in [
        ("conversation_participants", "is_pinned"),
        ("conversation_participants", "is_archived"),
        ("conversation_messages", "message_kind"),
        ("conversation_messages", "attachment_url"),
        ("conversation_messages", "attachment_name"),
        ("conversation_messages", "attachment_mime"),
        ("conversation_messages", "voice_duration_ms"),
        ("conversation_messages", "deleted_at"),
    ]:
        conn = op.get_bind()
        insp = sa.inspect(conn)
        if table in insp.get_table_names():
            cols = {c["name"] for c in insp.get_columns(table)}
            if col in cols:
                op.drop_column(table, col)
