"""Schemas for student activity tracking APIs."""

from pydantic import BaseModel, Field


class EngagementEventIn(BaseModel):
    event_type: str = Field(..., description="Engagement event type")
    resource_type: str | None = None
    resource_id: int | None = None
    path: str | None = None
    metadata: dict | None = None


class EngagementEventOut(BaseModel):
    id: int
    event_type: str
    resource_type: str | None = None
    resource_id: int | None = None
    path: str | None = None
    counted_seconds: int = 0
    occurred_at: str | None = None


class ActivitySessionOut(BaseModel):
    id: int
    login_at: str | None = None
    logout_at: str | None = None
    logout_reason: str | None = None
    active_minutes: int = 0
    auth_session_id: int | None = None


class StudentActivitySummaryOut(BaseModel):
    last_activity_at: str | None = None
    active_session_id: int | None = None
    session_login_at: str | None = None
    session_active_minutes: int = 0
    today_active_minutes: int = 0
    week_active_minutes: int = 0
    inactivity_threshold_minutes: int = 15
