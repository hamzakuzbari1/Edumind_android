"""Promotion test session registry — persisted in promotion_readiness_json (PR-C)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.progression import LanguageProgression
from app.services.language_promotion_test.session_storage import (
    clear_promotion_test_sessions,
    find_active_promotion_test_session,
    load_promotion_test_session,
    register_promotion_test_session,
    remove_promotion_test_session,
)
from app.services.language_promotion_test.types import PromotionTestSession


async def register_session(
    db: AsyncSession,
    session: PromotionTestSession,
    *,
    locked_row: LanguageProgression | None = None,
) -> PromotionTestSession:
    return await register_promotion_test_session(db, session, locked_row=locked_row)


async def get_session(
    db: AsyncSession,
    session_id: str,
    *,
    student_id: int,
    language_id: int,
) -> PromotionTestSession | None:
    return await load_promotion_test_session(
        db,
        session_id=session_id,
        student_id=student_id,
        language_id=language_id,
    )


async def pop_session(
    db: AsyncSession,
    session_id: str,
    *,
    student_id: int,
    language_id: int,
    locked_row: LanguageProgression | None = None,
) -> PromotionTestSession | None:
    return await remove_promotion_test_session(
        db,
        student_id=student_id,
        language_id=language_id,
        session_id=session_id,
        locked_row=locked_row,
    )


async def find_active_session(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> PromotionTestSession | None:
    return await find_active_promotion_test_session(
        db, student_id=student_id, language_id=language_id
    )


async def clear_sessions_for_tests(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> None:
    await clear_promotion_test_sessions(db, student_id=student_id, language_id=language_id)
