"""Shared server-side policy for language placement retakes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.models.language.profile import LanguageStudentProfile


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def placement_retake_days() -> int:
    """Return the configured cooldown; never allow a negative value."""
    return max(0, int(get_settings().LANGUAGE_PLACEMENT_RETAKE_DAYS))


def next_allowed_retake_at(completed_at: datetime) -> datetime:
    return _utc(completed_at) + timedelta(days=placement_retake_days())


def effective_next_allowed_retake_at(profile: LanguageStudentProfile) -> datetime | None:
    """Honor persisted policy, deriving it from historical completion data when absent."""
    if profile.next_allowed_retake_date:
        return _utc(profile.next_allowed_retake_date)
    anchor = profile.last_assessment_date or profile.placement_completed_at
    return next_allowed_retake_at(anchor) if anchor else None


def ensure_placement_retake_allowed(
    profile: LanguageStudentProfile,
    *,
    now: datetime | None = None,
) -> None:
    allow_at = effective_next_allowed_retake_at(profile)
    current = _utc(now or datetime.now(timezone.utc))
    if allow_at and current < allow_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "placement_retake_not_allowed",
                "message": "You cannot start another placement test yet.",
                "next_allowed_retake_date": allow_at.isoformat(),
            },
        )
