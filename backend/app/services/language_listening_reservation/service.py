"""Session Reservation Service — listening lesson pin (Phase 2.2)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.models.language.reservation import LanguageListeningReservation
from app.services.language_listening_reservation.storage import (
    create_reservation,
    is_expired,
    load_active_reservation,
    load_reservation_by_content,
    mark_completed,
    mark_expired,
    mark_skipped,
    mark_started,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ReservationResolveResult:
    content_item_id: int
    reservation_id: str
    lifecycle_state: str
    created_new: bool


class ListeningSessionReservationService:
    """Owns active listening lesson pin per (student_id, language_id)."""

    async def load_reserved_content_id(
        self,
        db: AsyncSession,
        *,
        student_id: int,
        language_id: int,
    ) -> int | None:
        row = await self._load_active_or_expire(db, student_id=student_id, language_id=language_id)
        return row.content_item_id if row else None

    async def resolve_reserved_lesson(
        self,
        db: AsyncSession,
        *,
        student_id: int,
        language_id: int,
        select_lesson_fn,
    ) -> ReservationResolveResult | None:
        """Return existing reservation or create one via deterministic selector."""
        existing = await self._load_active_or_expire(db, student_id=student_id, language_id=language_id)
        if existing is not None:
            await mark_started(db, existing)
            await db.commit()
            return ReservationResolveResult(
                content_item_id=existing.content_item_id,
                reservation_id=str(existing.id),
                lifecycle_state=str(existing.lifecycle_state),
                created_new=False,
            )

        item = await select_lesson_fn()
        if item is None:
            return None

        try:
            row = await create_reservation(
                db,
                student_id=student_id,
                language_id=language_id,
                content_item_id=item.id,
            )
            await mark_started(db, row)
            await db.commit()
            return ReservationResolveResult(
                content_item_id=row.content_item_id,
                reservation_id=str(row.id),
                lifecycle_state=str(row.lifecycle_state),
                created_new=True,
            )
        except IntegrityError:
            await db.rollback()
            logger.info(
                "Reservation race resolved student=%s language=%s — reloading active pin",
                student_id,
                language_id,
            )
            existing = await self._load_active_or_expire(
                db, student_id=student_id, language_id=language_id
            )
            if existing is None:
                return None
            await mark_started(db, existing)
            await db.commit()
            return ReservationResolveResult(
                content_item_id=existing.content_item_id,
                reservation_id=str(existing.id),
                lifecycle_state=str(existing.lifecycle_state),
                created_new=False,
            )

    async def complete_reservation(
        self,
        db: AsyncSession,
        *,
        student_id: int,
        language_id: int,
        content_item_id: int,
    ) -> LanguageListeningReservation | None:
        row = await load_reservation_by_content(
            db,
            student_id=student_id,
            language_id=language_id,
            content_item_id=content_item_id,
        )
        if row is None:
            return None
        await mark_completed(db, row)
        await db.commit()
        return row

    async def skip_reservation(
        self,
        db: AsyncSession,
        *,
        student_id: int,
        language_id: int,
        content_item_id: int | None = None,
    ) -> bool:
        row = await load_active_reservation(db, student_id=student_id, language_id=language_id)
        if row is None:
            return False
        if content_item_id is not None and row.content_item_id != content_item_id:
            return False
        await mark_skipped(db, row)
        await db.commit()
        return True

    async def touch_started(
        self,
        db: AsyncSession,
        *,
        student_id: int,
        language_id: int,
        content_item_id: int,
    ) -> None:
        row = await load_reservation_by_content(
            db,
            student_id=student_id,
            language_id=language_id,
            content_item_id=content_item_id,
        )
        if row is None:
            return
        await mark_started(db, row)
        await db.flush()

    async def _load_active_or_expire(
        self,
        db: AsyncSession,
        *,
        student_id: int,
        language_id: int,
    ) -> LanguageListeningReservation | None:
        row = await load_active_reservation(db, student_id=student_id, language_id=language_id)
        if row is None:
            return None
        if is_expired(row):
            await mark_expired(db, row)
            await db.commit()
            return None
        return row


listening_session_reservation_service = ListeningSessionReservationService()
