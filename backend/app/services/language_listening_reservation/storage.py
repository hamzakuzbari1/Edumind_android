"""Listening session reservation persistence (Phase 2.2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.reservation import LanguageListeningReservation
from app.services.language_listening_reservation.lifecycle import assert_transition
from app.services.language_listening_reservation.types import (
    ACTIVE_RESERVATION_STATES,
    ListeningLessonLifecycleState,
)

DEFAULT_RESERVATION_TTL_HOURS = 24


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _transition_row(
    row: LanguageListeningReservation,
    target: ListeningLessonLifecycleState,
    *,
    archive_reason: str | None = None,
) -> None:
    current = ListeningLessonLifecycleState(str(row.lifecycle_state))
    assert_transition(current, target)
    now = _utcnow()
    row.lifecycle_state = target.value
    row.updated_at = now
    if target == ListeningLessonLifecycleState.started:
        row.started_at = now
    elif target == ListeningLessonLifecycleState.completed:
        row.completed_at = now
    elif target == ListeningLessonLifecycleState.reviewed:
        row.reviewed_at = now
    elif target == ListeningLessonLifecycleState.archived:
        row.archived_at = now
        row.archive_reason = archive_reason


async def load_active_reservation(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LanguageListeningReservation | None:
    res = await db.execute(
        select(LanguageListeningReservation)
        .where(
            LanguageListeningReservation.student_id == student_id,
            LanguageListeningReservation.language_id == language_id,
            LanguageListeningReservation.lifecycle_state.in_(
                [s.value for s in ACTIVE_RESERVATION_STATES]
            ),
        )
        .order_by(LanguageListeningReservation.reserved_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def load_reservation_by_content(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    content_item_id: int,
) -> LanguageListeningReservation | None:
    res = await db.execute(
        select(LanguageListeningReservation).where(
            LanguageListeningReservation.student_id == student_id,
            LanguageListeningReservation.language_id == language_id,
            LanguageListeningReservation.content_item_id == content_item_id,
            LanguageListeningReservation.lifecycle_state.in_(
                [s.value for s in ACTIVE_RESERVATION_STATES]
            ),
        )
    )
    return res.scalar_one_or_none()


async def create_reservation(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    content_item_id: int,
    ttl_hours: int = DEFAULT_RESERVATION_TTL_HOURS,
) -> LanguageListeningReservation:
    now = _utcnow()
    row = LanguageListeningReservation(
        id=uuid.uuid4(),
        student_id=student_id,
        language_id=language_id,
        content_item_id=content_item_id,
        lifecycle_state=ListeningLessonLifecycleState.reserved.value,
        reserved_at=now,
        expires_at=now + timedelta(hours=ttl_hours),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return row


async def mark_started(db: AsyncSession, row: LanguageListeningReservation) -> LanguageListeningReservation:
    current = ListeningLessonLifecycleState(str(row.lifecycle_state))
    if current == ListeningLessonLifecycleState.started:
        return row
    _transition_row(row, ListeningLessonLifecycleState.started)
    await db.flush()
    return row


async def mark_completed(db: AsyncSession, row: LanguageListeningReservation) -> LanguageListeningReservation:
    current = ListeningLessonLifecycleState(str(row.lifecycle_state))
    if current == ListeningLessonLifecycleState.reserved:
        _transition_row(row, ListeningLessonLifecycleState.started)
    if ListeningLessonLifecycleState(str(row.lifecycle_state)) == ListeningLessonLifecycleState.started:
        _transition_row(row, ListeningLessonLifecycleState.completed)
    if ListeningLessonLifecycleState(str(row.lifecycle_state)) == ListeningLessonLifecycleState.completed:
        _transition_row(row, ListeningLessonLifecycleState.reviewed)
    await db.flush()
    return row


async def mark_skipped(db: AsyncSession, row: LanguageListeningReservation) -> LanguageListeningReservation:
    current = ListeningLessonLifecycleState(str(row.lifecycle_state))
    if current in ACTIVE_RESERVATION_STATES:
        _transition_row(row, ListeningLessonLifecycleState.archived, archive_reason="skipped")
    await db.flush()
    return row


async def mark_expired(db: AsyncSession, row: LanguageListeningReservation) -> LanguageListeningReservation:
    current = ListeningLessonLifecycleState(str(row.lifecycle_state))
    if current in ACTIVE_RESERVATION_STATES:
        _transition_row(row, ListeningLessonLifecycleState.archived, archive_reason="expired")
    await db.flush()
    return row


def is_expired(row: LanguageListeningReservation, *, now: datetime | None = None) -> bool:
    ref = now or _utcnow()
    return row.expires_at <= ref
