"""Subscription lifecycle: activated_at / expires_at on student_course_access."""

from alembic import op
import sqlalchemy as sa

revision = "0007_subscription_lifecycle"
down_revision = "0006_parent_link_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("student_course_access")}
    if "activated_at" not in cols:
        op.add_column(
            "student_course_access",
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "expires_at" not in cols:
        op.add_column(
            "student_course_access",
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_student_course_access_expires_at",
            "student_course_access",
            ["expires_at"],
            unique=False,
        )

    # Backfill paid rows: activated_at from unlocked_at/created_at, expires_at +30 days
    conn.execute(
        sa.text(
            """
            UPDATE student_course_access
            SET activated_at = COALESCE(unlocked_at, created_at, NOW()),
                expires_at = COALESCE(
                    expires_at,
                    COALESCE(unlocked_at, created_at, NOW()) + INTERVAL '30 days'
                )
            WHERE payment_status = 'paid'
              AND (activated_at IS NULL OR expires_at IS NULL)
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_student_course_access_expires_at", table_name="student_course_access")
    op.drop_column("student_course_access", "expires_at")
    op.drop_column("student_course_access", "activated_at")
