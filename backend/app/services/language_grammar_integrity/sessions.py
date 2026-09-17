"""Server-owned grammar activity sessions (Wave D)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.grammar_integrity import GrammarActivitySession
from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
from app.services.language_grammar_integrity.curriculum_version import get_curriculum_version
from app.services.language_grammar_integrity.errors import GrammarIntegrityError
from app.services.language_grammar_integrity.stamp import (
    DEFAULT_TTL_SECONDS,
    issue_signed_stamp,
    verify_signed_stamp,
)
from app.services.language_grammar_skill_context.types import SkillGrammarContext


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_skill(skill: GrammarEvidenceSourceSkill | str) -> str:
    if isinstance(skill, GrammarEvidenceSourceSkill):
        return skill.value
    key = str(skill or "").strip().lower()
    if key == "grammar":
        key = "grammar_lesson"
    return key


async def issue_activity_session(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    grammar_ctx: SkillGrammarContext,
    skill: GrammarEvidenceSourceSkill | str,
    activity_type: str = "",
    lesson_id: str = "",
    content_item_id: int | None = None,
    server_payload: dict[str, Any] | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> GrammarActivitySession:
    """Create a server session + signed stamp from a resolver-built grammar context.

    Fail closed if grammar_ctx is missing (caller must check).
    """
    if grammar_ctx is None:
        raise GrammarIntegrityError("resolver_empty", "Cannot issue session without resolved grammar")
    skill_key = _coerce_skill(skill)
    session_id = uuid.uuid4()
    curriculum_version = get_curriculum_version()
    now = _utcnow()
    stamp = issue_signed_stamp(
        session_id=str(session_id),
        student_id=student_id,
        language_id=language_id,
        grammar_id=grammar_ctx.grammar_id,
        skill=skill_key,
        activity_type=activity_type or skill_key,
        lesson_id=lesson_id or str(content_item_id or ""),
        content_item_id=content_item_id,
        curriculum_version=curriculum_version,
        ttl_seconds=ttl_seconds,
    )
    row = GrammarActivitySession(
        id=session_id,
        student_id=int(student_id),
        language_id=int(language_id),
        grammar_id=grammar_ctx.grammar_id,
        skill=skill_key,
        activity_type=(activity_type or skill_key),
        lesson_id=lesson_id or str(content_item_id or ""),
        content_item_id=content_item_id,
        status="open",
        stamp_token=stamp,
        curriculum_version=curriculum_version,
        server_payload_json=dict(server_payload or {}),
        expires_at=now + timedelta(seconds=max(60, ttl_seconds)),
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return row


async def get_activity_session(
    db: AsyncSession,
    *,
    activity_session_id: str | uuid.UUID,
) -> GrammarActivitySession | None:
    try:
        sid = uuid.UUID(str(activity_session_id))
    except ValueError as exc:
        raise GrammarIntegrityError("invalid_session_id", "activity_session_id is not a valid UUID") from exc
    return await db.get(GrammarActivitySession, sid)


async def load_owned_open_session(
    db: AsyncSession,
    *,
    activity_session_id: str | uuid.UUID,
    student_id: int,
) -> GrammarActivitySession:
    """Load session and enforce student ownership + stamp integrity."""
    row = await get_activity_session(db, activity_session_id=activity_session_id)
    if row is None:
        raise GrammarIntegrityError("session_not_found", "Activity session not found")
    if int(row.student_id) != int(student_id):
        raise GrammarIntegrityError("student_ownership", "Activity session belongs to another student")
    if row.status != "open":
        raise GrammarIntegrityError("session_not_open", f"Activity session status is {row.status}")
    if row.expires_at is not None and row.expires_at < _utcnow():
        raise GrammarIntegrityError("session_expired", "Activity session has expired")
    verify_signed_stamp(
        row.stamp_token,
        expected_session_id=str(row.id),
        expected_student_id=int(student_id),
        expected_grammar_id=row.grammar_id,
    )
    return row


async def mark_session_completed(
    db: AsyncSession,
    *,
    session: GrammarActivitySession,
) -> None:
    session.status = "completed"
    session.completed_at = _utcnow()
    session.updated_at = _utcnow()
    flag_modified(session, "server_payload_json")
    await db.flush()


async def find_open_session_for_content(
    db: AsyncSession,
    *,
    student_id: int,
    content_item_id: int,
    skill: str,
) -> GrammarActivitySession | None:
    result = await db.execute(
        select(GrammarActivitySession)
        .where(
            GrammarActivitySession.student_id == student_id,
            GrammarActivitySession.content_item_id == content_item_id,
            GrammarActivitySession.skill == skill,
            GrammarActivitySession.status == "open",
        )
        .order_by(GrammarActivitySession.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
