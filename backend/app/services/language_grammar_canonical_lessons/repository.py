"""Async persistence primitives for published canonical grammar lessons."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.grammar_canonical_lesson import (
    GrammarCanonicalLesson,
    GrammarCanonicalLessonRevision,
)
from app.services.language_grammar_canonical_lessons.errors import GrammarCanonicalLessonError
from app.services.language_grammar_canonical_lessons.hashing import compute_canonical_lesson_content_hash
from app.services.language_grammar_canonical_lessons.types import GrammarCanonicalRevisionStatus

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"generating"},
    "generating": {"validating", "failed"},
    "validating": {"reviewable", "failed"},
    "reviewable": {"published", "failed"},
    "published": {"archived"},
    "failed": {"draft"},
    "archived": set(),
}

_CONTENT_MUTABLE_STATUSES = {"draft", "generating", "validating"}
_ARCHIVABLE_STATUSES = {"draft", "generating", "validating", "reviewable", "failed", "published"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _status_value(status: GrammarCanonicalRevisionStatus | str) -> str:
    if isinstance(status, GrammarCanonicalRevisionStatus):
        return status.value
    return str(status)


def assert_transition_allowed(
    current_status: GrammarCanonicalRevisionStatus | str,
    next_status: GrammarCanonicalRevisionStatus | str,
) -> None:
    current = _status_value(current_status)
    next_ = _status_value(next_status)
    if next_ not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise GrammarCanonicalLessonError(
            "invalid_revision_transition",
            f"Cannot transition canonical grammar revision from {current!r} to {next_!r}",
        )


async def get_canonical_lesson_by_identity(
    db: AsyncSession,
    *,
    grammar_id: str,
    cefr_level: str,
    locale: str,
    methodology_version: str,
    for_update: bool = False,
) -> GrammarCanonicalLesson | None:
    stmt = select(GrammarCanonicalLesson).where(
        GrammarCanonicalLesson.grammar_id == grammar_id,
        GrammarCanonicalLesson.cefr_level == cefr_level,
        GrammarCanonicalLesson.locale == locale,
        GrammarCanonicalLesson.methodology_version == methodology_version,
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_canonical_lesson(
    db: AsyncSession,
    *,
    grammar_id: str,
    cefr_level: str,
    locale: str,
    methodology_version: str,
    now: datetime | None = None,
) -> GrammarCanonicalLesson:
    existing = await get_canonical_lesson_by_identity(
        db,
        grammar_id=grammar_id,
        cefr_level=cefr_level,
        locale=locale,
        methodology_version=methodology_version,
    )
    if existing is not None:
        return existing

    ts = now or utc_now()
    lesson = GrammarCanonicalLesson(
        id=uuid.uuid4(),
        grammar_id=grammar_id,
        cefr_level=cefr_level,
        locale=locale,
        methodology_version=methodology_version,
        created_at=ts,
        updated_at=ts,
    )
    db.add(lesson)
    await db.flush()
    return lesson


async def get_canonical_lesson_by_id(
    db: AsyncSession,
    *,
    lesson_id: uuid.UUID,
    for_update: bool = False,
) -> GrammarCanonicalLesson | None:
    stmt = select(GrammarCanonicalLesson).where(GrammarCanonicalLesson.id == lesson_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_next_draft_revision(
    db: AsyncSession,
    *,
    lesson_id: uuid.UUID,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevision:
    lesson = await get_canonical_lesson_by_id(db, lesson_id=lesson_id, for_update=True)
    if lesson is None:
        raise GrammarCanonicalLessonError("canonical_lesson_not_found", "Canonical grammar lesson was not found")

    result = await db.execute(
        select(func.max(GrammarCanonicalLessonRevision.revision_number)).where(
            GrammarCanonicalLessonRevision.lesson_id == lesson_id
        )
    )
    revision_number = int(result.scalar_one_or_none() or 0) + 1
    ts = now or utc_now()
    revision = GrammarCanonicalLessonRevision(
        id=uuid.uuid4(),
        lesson_id=lesson_id,
        revision_number=revision_number,
        status=GrammarCanonicalRevisionStatus.DRAFT.value,
        created_at=ts,
        updated_at=ts,
    )
    db.add(revision)
    await db.flush()
    return revision


async def read_revision_by_id(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    for_update: bool = False,
) -> GrammarCanonicalLessonRevision | None:
    stmt = select(GrammarCanonicalLessonRevision).where(GrammarCanonicalLessonRevision.id == revision_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_revisions_for_canonical_lesson(
    db: AsyncSession,
    *,
    lesson_id: uuid.UUID,
) -> list[GrammarCanonicalLessonRevision]:
    result = await db.execute(
        select(GrammarCanonicalLessonRevision)
        .where(GrammarCanonicalLessonRevision.lesson_id == lesson_id)
        .order_by(GrammarCanonicalLessonRevision.revision_number.asc())
    )
    return list(result.scalars().all())


async def store_or_update_draft_content(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    student_content_json: dict[str, Any],
    server_teaching_metadata_json: dict[str, Any],
    schema_version: str,
    prompt_version: str | None = None,
    catalog_version: str | None = None,
    authoring_provider: str | None = None,
    authoring_model: str | None = None,
    diagnostics_json: dict[str, Any] | None = None,
    raw_artifact_ref: str | None = None,
    generated_at: datetime | None = None,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevision:
    revision = await read_revision_by_id(db, revision_id=revision_id, for_update=True)
    if revision is None:
        raise GrammarCanonicalLessonError("revision_not_found", "Canonical grammar lesson revision was not found")
    if revision.status not in _CONTENT_MUTABLE_STATUSES:
        raise GrammarCanonicalLessonError(
            "revision_content_immutable",
            f"Cannot mutate educational content while revision status is {revision.status!r}",
        )

    lesson = await get_canonical_lesson_by_id(db, lesson_id=revision.lesson_id)
    if lesson is None:
        raise GrammarCanonicalLessonError("canonical_lesson_not_found", "Revision parent lesson was not found")

    ts = now or utc_now()
    revision.student_content_json = dict(student_content_json)
    revision.server_teaching_metadata_json = dict(server_teaching_metadata_json)
    revision.schema_version = schema_version
    revision.prompt_version = prompt_version
    revision.catalog_version = catalog_version
    revision.authoring_provider = authoring_provider
    revision.authoring_model = authoring_model
    revision.diagnostics_json = dict(diagnostics_json) if diagnostics_json is not None else None
    revision.raw_artifact_ref = raw_artifact_ref
    revision.generated_at = generated_at or ts
    revision.content_hash = compute_canonical_lesson_content_hash(
        student_content_json=revision.student_content_json,
        server_teaching_metadata_json=revision.server_teaching_metadata_json,
        schema_version=schema_version,
        methodology_version=lesson.methodology_version,
    )
    revision.updated_at = ts
    await db.flush()
    return revision


async def mark_revision_status(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    status: GrammarCanonicalRevisionStatus | str,
    diagnostics_json: dict[str, Any] | None = None,
    approved_by_user_id: int | None = None,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevision:
    revision = await read_revision_by_id(db, revision_id=revision_id, for_update=True)
    if revision is None:
        raise GrammarCanonicalLessonError("revision_not_found", "Canonical grammar lesson revision was not found")

    target_status = _status_value(status)
    assert_transition_allowed(revision.status, target_status)
    if target_status == GrammarCanonicalRevisionStatus.REVIEWABLE.value:
        _assert_revision_ready_for_review(revision)

    ts = now or utc_now()
    revision.status = target_status
    revision.updated_at = ts
    if diagnostics_json is not None:
        revision.diagnostics_json = dict(diagnostics_json)
    if target_status == GrammarCanonicalRevisionStatus.REVIEWABLE.value:
        revision.reviewed_at = ts
        revision.approved_by_user_id = approved_by_user_id
    if target_status == GrammarCanonicalRevisionStatus.FAILED.value and diagnostics_json is None:
        revision.diagnostics_json = {}
    if target_status == GrammarCanonicalRevisionStatus.ARCHIVED.value:
        revision.archived_at = ts
    await db.flush()
    return revision


async def mark_revision_generating(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevision:
    return await mark_revision_status(
        db,
        revision_id=revision_id,
        status=GrammarCanonicalRevisionStatus.GENERATING,
        now=now,
    )


async def mark_revision_validating(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevision:
    return await mark_revision_status(
        db,
        revision_id=revision_id,
        status=GrammarCanonicalRevisionStatus.VALIDATING,
        now=now,
    )


async def mark_revision_reviewable(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    approved_by_user_id: int | None = None,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevision:
    return await mark_revision_status(
        db,
        revision_id=revision_id,
        status=GrammarCanonicalRevisionStatus.REVIEWABLE,
        approved_by_user_id=approved_by_user_id,
        now=now,
    )


async def mark_revision_failed(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    diagnostics_json: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevision:
    return await mark_revision_status(
        db,
        revision_id=revision_id,
        status=GrammarCanonicalRevisionStatus.FAILED,
        diagnostics_json=diagnostics_json,
        now=now,
    )


async def archive_revision(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevision:
    revision = await read_revision_by_id(db, revision_id=revision_id, for_update=True)
    if revision is None:
        raise GrammarCanonicalLessonError("revision_not_found", "Canonical grammar lesson revision was not found")
    if revision.status not in _ARCHIVABLE_STATUSES:
        raise GrammarCanonicalLessonError("revision_not_archivable", f"Cannot archive status {revision.status!r}")

    ts = now or utc_now()
    revision.status = GrammarCanonicalRevisionStatus.ARCHIVED.value
    revision.archived_at = ts
    revision.updated_at = ts
    await db.flush()
    return revision


async def publish_reviewable_revision(
    db: AsyncSession,
    *,
    lesson_id: uuid.UUID,
    revision_id: uuid.UUID,
    approved_by_user_id: int | None = None,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevision:
    lesson = await get_canonical_lesson_by_id(db, lesson_id=lesson_id, for_update=True)
    if lesson is None:
        raise GrammarCanonicalLessonError("canonical_lesson_not_found", "Canonical grammar lesson was not found")

    candidate = await read_revision_by_id(db, revision_id=revision_id, for_update=True)
    if candidate is None:
        raise GrammarCanonicalLessonError("revision_not_found", "Candidate revision was not found")
    if candidate.lesson_id != lesson_id:
        raise GrammarCanonicalLessonError("revision_lesson_mismatch", "Candidate revision belongs to another lesson")
    if candidate.status != GrammarCanonicalRevisionStatus.REVIEWABLE.value:
        raise GrammarCanonicalLessonError(
            "revision_not_publishable",
            f"Only reviewable revisions can be published; got {candidate.status!r}",
        )
    _assert_revision_ready_for_review(candidate)

    ts = now or utc_now()
    current = await get_active_published_revision_by_lesson_id(db, lesson_id=lesson_id, for_update=True)
    if current is not None and current.id != candidate.id:
        current.status = GrammarCanonicalRevisionStatus.ARCHIVED.value
        current.archived_at = ts
        current.updated_at = ts
        await db.flush()

    candidate.status = GrammarCanonicalRevisionStatus.PUBLISHED.value
    candidate.published_at = ts
    candidate.updated_at = ts
    if candidate.reviewed_at is None:
        candidate.reviewed_at = ts
    if approved_by_user_id is not None:
        candidate.approved_by_user_id = approved_by_user_id
    await db.flush()
    return candidate


async def get_active_published_revision_by_lesson_id(
    db: AsyncSession,
    *,
    lesson_id: uuid.UUID,
    for_update: bool = False,
) -> GrammarCanonicalLessonRevision | None:
    stmt = select(GrammarCanonicalLessonRevision).where(
        GrammarCanonicalLessonRevision.lesson_id == lesson_id,
        GrammarCanonicalLessonRevision.status == GrammarCanonicalRevisionStatus.PUBLISHED.value,
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_active_published_revision_by_identity(
    db: AsyncSession,
    *,
    grammar_id: str,
    cefr_level: str,
    locale: str,
    methodology_version: str,
) -> GrammarCanonicalLessonRevision | None:
    lesson = await get_canonical_lesson_by_identity(
        db,
        grammar_id=grammar_id,
        cefr_level=cefr_level,
        locale=locale,
        methodology_version=methodology_version,
    )
    if lesson is None:
        return None
    return await get_active_published_revision_by_lesson_id(db, lesson_id=lesson.id)


def _assert_revision_ready_for_review(revision: GrammarCanonicalLessonRevision) -> None:
    if not revision.student_content_json:
        raise GrammarCanonicalLessonError("missing_student_content", "Revision has no student content")
    if not revision.server_teaching_metadata_json:
        raise GrammarCanonicalLessonError("missing_server_teaching_metadata", "Revision has no teaching metadata")
    if not revision.schema_version:
        raise GrammarCanonicalLessonError("missing_schema_version", "Revision has no schema version")
    if not revision.content_hash:
        raise GrammarCanonicalLessonError("missing_content_hash", "Revision has no deterministic content hash")
