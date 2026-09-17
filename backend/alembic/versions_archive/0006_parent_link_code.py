"""Add parent_link_code to student_profiles."""

from alembic import op
import sqlalchemy as sa

revision = "0006_parent_link_code"
down_revision = "0005_production_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("student_profiles")}
    if "parent_link_code" not in cols:
        op.add_column(
            "student_profiles",
            sa.Column("parent_link_code", sa.String(length=16), nullable=True),
        )
        op.create_index(
            "ix_student_profiles_parent_link_code",
            "student_profiles",
            ["parent_link_code"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("ix_student_profiles_parent_link_code", table_name="student_profiles")
    op.drop_column("student_profiles", "parent_link_code")
