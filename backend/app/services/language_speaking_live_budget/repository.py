"""DB access for S13 live budget — row locks + get-or-create."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.speaking_live_budget import SpeakingLiveDailyUsage, SpeakingLiveLease
from app.services.language_speaking_live_budget.policy import POLICY_VERSION, utc_now


async def lock_or_create_daily_usage(
    db: AsyncSession,
    *,
    student_id: int,
    usage_date: date,
    now: datetime | None = None,
) -> SpeakingLiveDailyUsage:
    """Exclusive lock on today's usage row (create if missing).

    Uses SELECT ... FOR UPDATE. Concurrent authors serialize on the unique
    (student_id, usage_date) constraint via retry on IntegrityError at caller
    if needed; the common path locks the existing row.
    """
    ts = now or utc_now()
    result = await db.execute(
        select(SpeakingLiveDailyUsage)
        .where(
            SpeakingLiveDailyUsage.student_id == student_id,
            SpeakingLiveDailyUsage.usage_date == usage_date,
        )
        .with_for_update()
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row

    row = SpeakingLiveDailyUsage(
        id=uuid.uuid4(),
        student_id=student_id,
        usage_date=usage_date,
        consumed_seconds=0,
        policy_version=POLICY_VERSION,
        created_at=ts,
        updated_at=ts,
    )
    db.add(row)
    await db.flush()
    # Re-select with lock so concurrent creators serialize.
    result = await db.execute(
        select(SpeakingLiveDailyUsage)
        .where(
            SpeakingLiveDailyUsage.student_id == student_id,
            SpeakingLiveDailyUsage.usage_date == usage_date,
        )
        .with_for_update()
    )
    locked = result.scalar_one()
    return locked


async def get_daily_usage(
    db: AsyncSession,
    *,
    student_id: int,
    usage_date: date,
    for_update: bool = False,
) -> SpeakingLiveDailyUsage | None:
    stmt = select(SpeakingLiveDailyUsage).where(
        SpeakingLiveDailyUsage.student_id == student_id,
        SpeakingLiveDailyUsage.usage_date == usage_date,
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_active_lease_for_student(
    db: AsyncSession,
    *,
    student_id: int,
    for_update: bool = False,
) -> SpeakingLiveLease | None:
    stmt = select(SpeakingLiveLease).where(
        SpeakingLiveLease.student_id == student_id,
        SpeakingLiveLease.status == "active",
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_lease_by_id(
    db: AsyncSession,
    *,
    lease_id: uuid.UUID,
    for_update: bool = False,
) -> SpeakingLiveLease | None:
    stmt = select(SpeakingLiveLease).where(SpeakingLiveLease.id == lease_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_stale_active_leases(
    db: AsyncSession,
    *,
    student_id: int,
    stale_before: datetime,
    for_update: bool = True,
) -> list[SpeakingLiveLease]:
    stmt = select(SpeakingLiveLease).where(
        SpeakingLiveLease.student_id == student_id,
        SpeakingLiveLease.status == "active",
        SpeakingLiveLease.last_heartbeat_at < stale_before,
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    return list(result.scalars().all())


def create_lease(
    *,
    student_id: int,
    usage_date: date,
    started_at: datetime,
    deadline_at: datetime,
) -> SpeakingLiveLease:
    return SpeakingLiveLease(
        id=uuid.uuid4(),
        student_id=student_id,
        usage_date=usage_date,
        status="active",
        started_at=started_at,
        last_heartbeat_at=started_at,
        deadline_at=deadline_at,
        accounted_seconds=0,
        created_at=started_at,
        updated_at=started_at,
    )
