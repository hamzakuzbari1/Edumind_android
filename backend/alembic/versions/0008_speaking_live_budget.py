"""Add speaking live daily usage + lease tables (S13).

Revision ID: 0008_speaking_live_budget
Revises: 0007_placement_qbank
Create Date: 2026-07-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_speaking_live_budget"
down_revision = "0007_placement_qbank"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "speaking_live_daily_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("consumed_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "usage_date", name="uq_speaking_live_daily_usage_student_date"),
    )
    op.create_index(
        "ix_speaking_live_daily_usage_student_id",
        "speaking_live_daily_usage",
        ["student_id"],
    )
    op.create_index(
        "ix_speaking_live_daily_usage_usage_date",
        "speaking_live_daily_usage",
        ["usage_date"],
    )

    op.create_table(
        "speaking_live_leases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accounted_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_speaking_live_leases_student_id",
        "speaking_live_leases",
        ["student_id"],
    )
    op.create_index(
        "ix_speaking_live_leases_usage_date",
        "speaking_live_leases",
        ["usage_date"],
    )
    op.create_index(
        "ix_speaking_live_leases_student_status",
        "speaking_live_leases",
        ["student_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_speaking_live_leases_student_status", table_name="speaking_live_leases")
    op.drop_index("ix_speaking_live_leases_usage_date", table_name="speaking_live_leases")
    op.drop_index("ix_speaking_live_leases_student_id", table_name="speaking_live_leases")
    op.drop_table("speaking_live_leases")
    op.drop_index("ix_speaking_live_daily_usage_usage_date", table_name="speaking_live_daily_usage")
    op.drop_index("ix_speaking_live_daily_usage_student_id", table_name="speaking_live_daily_usage")
    op.drop_table("speaking_live_daily_usage")
