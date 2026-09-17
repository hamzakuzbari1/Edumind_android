"""Separate course enrollment lifecycle from access entitlement state.

Revision ID: 0017_course_enrollment_entitlements
Revises: 0016_course_units
Create Date: 2026-09-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0017_course_enrollment_entitlements"
down_revision = "0016_course_units"
branch_labels = None
depends_on = None


ENROLLMENT_STATUSES = "'pending', 'active', 'paused', 'completed', 'withdrawn', 'cancelled'"
CURRENT_ENROLLMENT_STATUSES = "'pending', 'active', 'paused'"
ENTITLEMENT_SOURCES = "'payment', 'manual_grant', 'promotion', 'admin', 'import', 'legacy'"
ACCESS_STATUSES = "'pending', 'active', 'suspended', 'expired', 'revoked'"


def upgrade() -> None:
    op.create_table(
        "course_enrollments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_payment_item_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            f"status IN ({ENROLLMENT_STATUSES})",
            name="ck_course_enrollments_status",
        ),
        sa.CheckConstraint(
            f"source IN ({ENTITLEMENT_SOURCES})",
            name="ck_course_enrollments_source",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            name="fk_course_enrollments_student_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_course_enrollments_course_id_courses",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_payment_item_id"],
            ["payment_items.id"],
            name="fk_course_enrollments_source_payment_item_id_payment_items",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_course_enrollments_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_course_enrollments"),
    )
    op.create_index(
        "ix_course_enrollments_student_course",
        "course_enrollments",
        ["student_id", "course_id"],
    )
    op.create_index(
        "ix_course_enrollments_course_student",
        "course_enrollments",
        ["course_id", "student_id"],
    )
    op.create_index(
        "ix_course_enrollments_status",
        "course_enrollments",
        ["status"],
    )
    op.create_index(
        "uq_course_enrollments_current_student_course",
        "course_enrollments",
        ["student_id", "course_id"],
        unique=True,
        postgresql_where=sa.text(
            f"status IN ({CURRENT_ENROLLMENT_STATUSES})"
        ),
    )

    op.add_column("student_course_access", sa.Column("enrollment_id", sa.Integer(), nullable=True))
    op.add_column("student_course_access", sa.Column("access_status", sa.String(length=24), nullable=True))
    op.add_column("student_course_access", sa.Column("source", sa.String(length=32), nullable=True))
    op.add_column(
        "student_course_access",
        sa.Column("source_payment_item_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "student_course_access",
        sa.Column("granted_by_user_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "student_course_access",
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "student_course_access",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "student_course_access",
        sa.Column("revocation_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_course_access",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_student_course_access_access_status",
        "student_course_access",
        f"access_status IS NULL OR access_status IN ({ACCESS_STATUSES})",
    )
    op.create_foreign_key(
        "fk_student_course_access_enrollment_id_course_enrollments",
        "student_course_access",
        "course_enrollments",
        ["enrollment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_student_course_access_source_payment_item_id_payment_items",
        "student_course_access",
        "payment_items",
        ["source_payment_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_student_course_access_granted_by_user_id_users",
        "student_course_access",
        "users",
        ["granted_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            WITH payment_matches AS (
                SELECT
                    access.id AS access_id,
                    count(item.id) AS match_count,
                    min(item.id) AS payment_item_id,
                    max(payment.paid_at) FILTER (WHERE item.id IS NOT NULL) AS paid_at
                FROM student_course_access AS access
                LEFT JOIN payments AS payment
                  ON payment.student_id = access.student_id
                 AND payment.status = 'paid'
                LEFT JOIN payment_items AS item
                  ON item.payment_id = payment.id
                 AND item.course_id = access.course_id
                 AND item.product_type = 'course'
                WHERE access.payment_status = 'paid'
                GROUP BY access.id
            )
            INSERT INTO course_enrollments (
                student_id,
                course_id,
                status,
                source,
                source_payment_item_id,
                created_by_user_id,
                enrolled_at,
                started_at,
                completed_at,
                withdrawn_at,
                created_at,
                updated_at
            )
            SELECT
                access.student_id,
                access.course_id,
                'active',
                CASE WHEN matches.match_count = 1 THEN 'payment' ELSE 'legacy' END,
                CASE WHEN matches.match_count = 1 THEN matches.payment_item_id ELSE NULL END,
                NULL,
                coalesce(
                    access.activated_at,
                    access.unlocked_at,
                    matches.paid_at,
                    access.created_at,
                    now()
                ),
                coalesce(access.activated_at, access.unlocked_at),
                NULL,
                NULL,
                coalesce(access.created_at, now()),
                now()
            FROM student_course_access AS access
            LEFT JOIN payment_matches AS matches ON matches.access_id = access.id
            WHERE access.payment_status = 'paid'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE student_course_access AS access
            SET
                enrollment_id = enrollment.id,
                access_status = CASE
                    WHEN access.expires_at IS NOT NULL AND access.expires_at <= now()
                        THEN 'expired'
                    ELSE 'active'
                END,
                source = enrollment.source,
                source_payment_item_id = enrollment.source_payment_item_id,
                granted_at = coalesce(
                    access.activated_at,
                    access.unlocked_at,
                    enrollment.enrolled_at,
                    access.created_at
                ),
                updated_at = now()
            FROM course_enrollments AS enrollment
            WHERE access.student_id = enrollment.student_id
              AND access.course_id = enrollment.course_id
              AND access.payment_status = 'paid'
              AND enrollment.status = 'active'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE student_course_access
            SET access_status = 'pending', updated_at = now()
            WHERE payment_status = 'pending'
              AND enrollment_id IS NULL
            """
        )
    )

    missing_paid_enrollments = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM student_course_access
            WHERE payment_status = 'paid'
              AND (enrollment_id IS NULL OR access_status NOT IN ('active', 'expired'))
            """
        )
    ).scalar_one()
    non_paid_enrollments = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM student_course_access
            WHERE payment_status <> 'paid' AND enrollment_id IS NOT NULL
            """
        )
    ).scalar_one()
    mismatched_enrollments = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM student_course_access AS access
            JOIN course_enrollments AS enrollment ON enrollment.id = access.enrollment_id
            WHERE access.student_id IS DISTINCT FROM enrollment.student_id
               OR access.course_id IS DISTINCT FROM enrollment.course_id
            """
        )
    ).scalar_one()
    invalid_payment_links = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM course_enrollments AS enrollment
            JOIN payment_items AS item ON item.id = enrollment.source_payment_item_id
            JOIN payments AS payment ON payment.id = item.payment_id
            WHERE enrollment.source = 'payment'
              AND (
                  item.course_id IS DISTINCT FROM enrollment.course_id
                  OR payment.student_id IS DISTINCT FROM enrollment.student_id
                  OR payment.status <> 'paid'
              )
            """
        )
    ).scalar_one()
    if (
        missing_paid_enrollments
        or non_paid_enrollments
        or mismatched_enrollments
        or invalid_payment_links
    ):
        raise RuntimeError(
            "Enrollment/entitlement backfill validation failed: "
            f"missing_paid={missing_paid_enrollments}, "
            f"non_paid_linked={non_paid_enrollments}, "
            f"mismatched={mismatched_enrollments}, "
            f"invalid_payment_links={invalid_payment_links}"
        )


def downgrade() -> None:
    op.drop_constraint(
        "fk_student_course_access_granted_by_user_id_users",
        "student_course_access",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_student_course_access_source_payment_item_id_payment_items",
        "student_course_access",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_student_course_access_enrollment_id_course_enrollments",
        "student_course_access",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_student_course_access_access_status",
        "student_course_access",
        type_="check",
    )
    for column in (
        "updated_at",
        "revocation_reason",
        "revoked_at",
        "granted_at",
        "granted_by_user_id",
        "source_payment_item_id",
        "source",
        "access_status",
        "enrollment_id",
    ):
        op.drop_column("student_course_access", column)
    op.drop_table("course_enrollments")
