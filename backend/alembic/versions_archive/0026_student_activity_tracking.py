"""Student activity tracking foundation — sessions, engagement events, last_activity_at."""

from alembic import op
import sqlalchemy as sa

revision = "0026_student_activity_tracking"
down_revision = "0025_two_factor_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "student_profiles",
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_student_profiles_last_activity_at",
        "student_profiles",
        ["last_activity_at"],
    )

    op.create_table(
        "student_activity_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("auth_session_id", sa.Integer(), nullable=True),
        sa.Column("login_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("logout_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "logout_reason",
            sa.Enum(
                "logout",
                "expired",
                "inactivity",
                name="activitysessionlogoutreason",
            ),
            nullable=True,
        ),
        sa.Column("active_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["auth_session_id"], ["auth_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_activity_sessions_student_id", "student_activity_sessions", ["student_id"])
    op.create_index("ix_student_activity_sessions_auth_session_id", "student_activity_sessions", ["auth_session_id"])
    op.create_index("ix_student_activity_sessions_login_at", "student_activity_sessions", ["login_at"])
    op.create_index("ix_student_activity_sessions_logout_at", "student_activity_sessions", ["logout_at"])
    op.create_index("ix_student_activity_sessions_created_at", "student_activity_sessions", ["created_at"])

    op.create_table(
        "student_engagement_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("activity_session_id", sa.Integer(), nullable=True),
        sa.Column(
            "event_type",
            sa.Enum(
                "login",
                "logout",
                "session_expired",
                "session_inactive",
                "lesson_opened",
                "lesson_viewed",
                "lesson_completed",
                "quiz_started",
                "quiz_submitted",
                "planner_activity",
                "messaging_activity",
                "page_navigation",
                name="engagementeventtype",
            ),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("path", sa.String(length=512), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("counted_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["activity_session_id"], ["student_activity_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_engagement_events_student_id", "student_engagement_events", ["student_id"])
    op.create_index(
        "ix_student_engagement_events_activity_session_id",
        "student_engagement_events",
        ["activity_session_id"],
    )
    op.create_index("ix_student_engagement_events_event_type", "student_engagement_events", ["event_type"])
    op.create_index("ix_student_engagement_events_occurred_at", "student_engagement_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_student_engagement_events_occurred_at", table_name="student_engagement_events")
    op.drop_index("ix_student_engagement_events_event_type", table_name="student_engagement_events")
    op.drop_index("ix_student_engagement_events_activity_session_id", table_name="student_engagement_events")
    op.drop_index("ix_student_engagement_events_student_id", table_name="student_engagement_events")
    op.drop_table("student_engagement_events")

    op.drop_index("ix_student_activity_sessions_created_at", table_name="student_activity_sessions")
    op.drop_index("ix_student_activity_sessions_logout_at", table_name="student_activity_sessions")
    op.drop_index("ix_student_activity_sessions_login_at", table_name="student_activity_sessions")
    op.drop_index("ix_student_activity_sessions_auth_session_id", table_name="student_activity_sessions")
    op.drop_index("ix_student_activity_sessions_student_id", table_name="student_activity_sessions")
    op.drop_table("student_activity_sessions")

    op.drop_index("ix_student_profiles_last_activity_at", table_name="student_profiles")
    op.drop_column("student_profiles", "last_activity_at")
