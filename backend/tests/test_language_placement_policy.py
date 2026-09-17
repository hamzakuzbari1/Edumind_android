"""Unit tests for the shared server-side placement retake policy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import language_placement_policy_service as policy


def _profile(**overrides):
    values = {
        "next_allowed_retake_date": None,
        "last_assessment_date": None,
        "placement_completed_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_retake_policy_uses_configured_days_instead_of_a_hardcoded_value(monkeypatch):
    monkeypatch.setattr(
        policy,
        "get_settings",
        lambda: SimpleNamespace(LANGUAGE_PLACEMENT_RETAKE_DAYS=37),
    )
    completed_at = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)

    assert policy.next_allowed_retake_at(completed_at) == completed_at + timedelta(days=37)


def test_persisted_next_allowed_date_takes_precedence_over_derived_date(monkeypatch):
    monkeypatch.setattr(
        policy,
        "get_settings",
        lambda: SimpleNamespace(LANGUAGE_PLACEMENT_RETAKE_DAYS=90),
    )
    explicit = datetime(2026, 8, 1, tzinfo=timezone.utc)
    profile = _profile(
        next_allowed_retake_date=explicit,
        last_assessment_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert policy.effective_next_allowed_retake_at(profile) == explicit


def test_direct_api_retake_before_allowed_date_is_rejected_with_date():
    allow_at = datetime(2026, 8, 1, 9, 30, tzinfo=timezone.utc)
    profile = _profile(next_allowed_retake_date=allow_at)

    with pytest.raises(HTTPException) as exc_info:
        policy.ensure_placement_retake_allowed(
            profile,
            now=datetime(2026, 7, 31, 9, 30, tzinfo=timezone.utc),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "placement_retake_not_allowed"
    assert exc_info.value.detail["next_allowed_retake_date"] == allow_at.isoformat()


def test_retake_is_allowed_at_the_exact_boundary():
    allow_at = datetime(2026, 8, 1, 9, 30, tzinfo=timezone.utc)
    profile = _profile(next_allowed_retake_date=allow_at)

    policy.ensure_placement_retake_allowed(profile, now=allow_at)


def test_naive_historical_dates_are_normalized_to_utc(monkeypatch):
    monkeypatch.setattr(
        policy,
        "get_settings",
        lambda: SimpleNamespace(LANGUAGE_PLACEMENT_RETAKE_DAYS=5),
    )
    profile = _profile(last_assessment_date=datetime(2026, 2, 1, 6, 0))

    result = policy.effective_next_allowed_retake_at(profile)

    assert result == datetime(2026, 2, 6, 6, 0, tzinfo=timezone.utc)
