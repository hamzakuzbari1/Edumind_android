"""Operator-controlled offline workflow for canonical grammar lessons."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.grammar_canonical_lesson import (
    GrammarCanonicalLesson,
    GrammarCanonicalLessonRevision,
)
from app.services.language_grammar.enums import GrammarCEFRBand
from app.services.language_grammar.id_canon import normalize_grammar_id
from app.services.language_grammar_catalog.catalog import require_topic
from app.services.language_grammar_canonical_authoring.artifacts import (
    write_raw_authoring_artifact,
    write_student_safe_review_artifact,
    write_student_safe_review_html_artifact,
)
from app.services.language_grammar_canonical_authoring.errors import (
    GrammarCanonicalAuthoringWorkflowError,
)
from app.services.language_grammar_canonical_authoring.inspection import (
    build_student_safe_inspection,
)
from app.services.language_grammar_canonical_authoring.types import (
    CanonicalAuthoringAdapter,
    CanonicalAuthoringAdapterRequest,
    CanonicalAuthoringAdapterResult,
    CanonicalLessonIdentityInput,
    DEFAULT_CATALOG_VERSION,
    DEFAULT_METHODOLOGY_VERSION,
    DEFAULT_PROMPT_VERSION,
    DEFAULT_SCHEMA_VERSION,
    SUPPORTED_AUTHORING_LOCALES,
    WorkflowCommandResult,
)
from app.services.language_grammar_canonical_authoring.validation import (
    safe_diagnostics,
    validate_persisted_revision_payload,
    validate_raw_authoring_output,
)
from app.services.language_grammar_canonical_lessons import (
    GrammarCanonicalLessonError,
    GrammarCanonicalRevisionStatus,
    archive_revision,
    create_next_draft_revision,
    get_active_published_revision_by_lesson_id,
    get_canonical_lesson_by_id,
    get_canonical_lesson_by_identity,
    get_or_create_canonical_lesson,
    list_revisions_for_canonical_lesson,
    mark_revision_failed,
    mark_revision_generating,
    mark_revision_reviewable,
    mark_revision_status,
    mark_revision_validating,
    publish_reviewable_revision,
    read_revision_by_id,
    store_or_update_draft_content,
)
from app.services.language_grammar_pipeline.stages import _grammar_authoring_profile


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_identity_input(identity: CanonicalLessonIdentityInput) -> CanonicalLessonIdentityInput:
    grammar_id = normalize_grammar_id(identity.grammar_id)
    try:
        require_topic(grammar_id)
    except KeyError as exc:
        raise GrammarCanonicalAuthoringWorkflowError("invalid_grammar_target", str(exc)) from exc
    try:
        cefr = GrammarCEFRBand(identity.cefr_level.upper()).value
    except ValueError as exc:
        raise GrammarCanonicalAuthoringWorkflowError(
            "invalid_cefr_level",
            f"Unsupported CEFR level: {identity.cefr_level}",
        ) from exc
    locale = identity.locale.strip()
    if locale not in SUPPORTED_AUTHORING_LOCALES:
        raise GrammarCanonicalAuthoringWorkflowError("invalid_locale", f"Unsupported locale: {locale}")
    methodology = identity.methodology_version.strip() or DEFAULT_METHODOLOGY_VERSION
    return CanonicalLessonIdentityInput(
        grammar_id=grammar_id,
        cefr_level=cefr,
        locale=locale,
        methodology_version=methodology,
    )


async def ensure_identity(
    db: AsyncSession,
    identity: CanonicalLessonIdentityInput,
) -> WorkflowCommandResult:
    normalized = normalize_identity_input(identity)
    existing = await get_canonical_lesson_by_identity(
        db,
        grammar_id=normalized.grammar_id,
        cefr_level=normalized.cefr_level,
        locale=normalized.locale,
        methodology_version=normalized.methodology_version,
    )
    lesson = await get_or_create_canonical_lesson(
        db,
        grammar_id=normalized.grammar_id,
        cefr_level=normalized.cefr_level,
        locale=normalized.locale,
        methodology_version=normalized.methodology_version,
    )
    return WorkflowCommandResult(
        ok=True,
        data={
            "canonical_lesson_id": str(lesson.id),
            "grammar_id": lesson.grammar_id,
            "cefr_level": lesson.cefr_level,
            "locale": lesson.locale,
            "methodology_version": lesson.methodology_version,
            "created": existing is None,
        },
    )


async def generate_draft_revision(
    db: AsyncSession,
    *,
    identity: CanonicalLessonIdentityInput,
    adapter: CanonicalAuthoringAdapter,
    artifact_dir: Path | None = None,
) -> WorkflowCommandResult:
    identity_result = await ensure_identity(db, identity)
    lesson = await get_canonical_lesson_by_id(
        db,
        lesson_id=uuid.UUID(identity_result.data["canonical_lesson_id"]),
        for_update=True,
    )
    if lesson is None:
        raise GrammarCanonicalAuthoringWorkflowError("canonical_lesson_not_found", "Identity was not persisted")

    revision = await create_next_draft_revision(db, lesson_id=lesson.id)
    await mark_revision_generating(db, revision_id=revision.id)
    profile = _grammar_authoring_profile((lesson.grammar_id,))
    topic_display_name = str(profile.get("display_name") or lesson.grammar_id)
    request = CanonicalAuthoringAdapterRequest(
        grammar_id=lesson.grammar_id,
        display_name=topic_display_name,
        cefr_level=lesson.cefr_level,
        locale=lesson.locale,
        methodology_version=lesson.methodology_version,
        schema_version=DEFAULT_SCHEMA_VERSION,
        prompt_version=DEFAULT_PROMPT_VERSION,
        catalog_version=DEFAULT_CATALOG_VERSION,
        grammar_profile=profile,
        learner_signals={"source": "offline_authoring", "synthetic": True},
    )

    try:
        result = adapter.generate(request)
    except Exception as exc:  # noqa: BLE001
        await mark_revision_failed(
            db,
            revision_id=revision.id,
            diagnostics_json=safe_diagnostics("provider_failure", str(exc)),
        )
        return _revision_result(False, lesson, revision, "provider_failure")

    if not result.success:
        artifact_ref = _write_artifact_if_present(revision, result, artifact_dir=artifact_dir, success=False)
        revision.raw_artifact_ref = artifact_ref or result.raw_artifact_ref
        revision.authoring_provider = result.provider_id
        revision.authoring_model = result.authoring_model
        revision.prompt_version = result.prompt_version
        revision.catalog_version = result.catalog_version
        revision.schema_version = result.schema_version
        revision.diagnostics_json = dict(result.diagnostics_json or safe_diagnostics("provider_failure", "Provider failed"))
        await mark_revision_failed(db, revision_id=revision.id, diagnostics_json=revision.diagnostics_json)
        return _revision_result(False, lesson, revision, "provider_failure")

    await mark_revision_validating(db, revision_id=revision.id)
    artifact_ref = _write_artifact_if_present(revision, result, artifact_dir=artifact_dir, success=True)
    raw_or_structured = _raw_or_structured_output(result)
    validation = validate_raw_authoring_output(raw_or_structured, lesson=lesson)
    if not validation.valid:
        revision.raw_artifact_ref = artifact_ref or result.raw_artifact_ref
        revision.authoring_provider = result.provider_id
        revision.authoring_model = result.authoring_model
        revision.prompt_version = result.prompt_version
        revision.catalog_version = result.catalog_version
        revision.schema_version = result.schema_version
        await mark_revision_failed(db, revision_id=revision.id, diagnostics_json=validation.diagnostics_json)
        return _revision_result(False, lesson, revision, validation.diagnostics_json.get("code", "validation_failed"))

    stored = await store_or_update_draft_content(
        db,
        revision_id=revision.id,
        student_content_json=validation.normalized_student_content or {},
        server_teaching_metadata_json=validation.normalized_server_teaching_metadata or {},
        schema_version=result.schema_version or DEFAULT_SCHEMA_VERSION,
        prompt_version=result.prompt_version or DEFAULT_PROMPT_VERSION,
        catalog_version=result.catalog_version or DEFAULT_CATALOG_VERSION,
        authoring_provider=result.provider_id,
        authoring_model=result.authoring_model,
        diagnostics_json={"status": "valid"},
        raw_artifact_ref=artifact_ref or result.raw_artifact_ref,
        generated_at=result.generated_at or utc_now(),
    )
    await mark_revision_reviewable(db, revision_id=stored.id)
    return _revision_result(True, lesson, stored, "reviewable")


async def validate_revision(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
) -> WorkflowCommandResult:
    revision = await _load_revision(db, revision_id=revision_id, for_update=True)
    lesson = await _load_lesson(db, lesson_id=revision.lesson_id)
    readonly = revision.status in {
        GrammarCanonicalRevisionStatus.PUBLISHED.value,
        GrammarCanonicalRevisionStatus.ARCHIVED.value,
    }
    validation = validate_persisted_revision_payload(
        lesson=lesson,
        revision=revision,
        require_existing_hash=revision.status
        in {
            GrammarCanonicalRevisionStatus.REVIEWABLE.value,
            GrammarCanonicalRevisionStatus.PUBLISHED.value,
            GrammarCanonicalRevisionStatus.ARCHIVED.value,
        },
    )
    if readonly:
        return _revision_result(validation.valid, lesson, revision, validation.diagnostics_json.get("code", "checked_read_only"))

    if not validation.valid:
        await _mark_failed_from_any_mutable_state(db, revision, validation.diagnostics_json)
        return _revision_result(False, lesson, revision, validation.diagnostics_json.get("code", "validation_failed"))

    if revision.status in {GrammarCanonicalRevisionStatus.DRAFT.value, GrammarCanonicalRevisionStatus.FAILED.value}:
        if revision.status == GrammarCanonicalRevisionStatus.FAILED.value:
            await mark_revision_status(db, revision_id=revision.id, status=GrammarCanonicalRevisionStatus.DRAFT)
        await mark_revision_generating(db, revision_id=revision.id)
        await mark_revision_validating(db, revision_id=revision.id)
        await store_or_update_draft_content(
            db,
            revision_id=revision.id,
            student_content_json=validation.normalized_student_content or {},
            server_teaching_metadata_json=validation.normalized_server_teaching_metadata or {},
            schema_version=revision.schema_version or DEFAULT_SCHEMA_VERSION,
            prompt_version=revision.prompt_version,
            catalog_version=revision.catalog_version,
            authoring_provider=revision.authoring_provider,
            authoring_model=revision.authoring_model,
            diagnostics_json={"status": "valid"},
            raw_artifact_ref=revision.raw_artifact_ref,
            generated_at=revision.generated_at,
        )
        await mark_revision_reviewable(db, revision_id=revision.id)
    elif revision.status == GrammarCanonicalRevisionStatus.GENERATING.value:
        await mark_revision_validating(db, revision_id=revision.id)
        await mark_revision_reviewable(db, revision_id=revision.id)
    elif revision.status == GrammarCanonicalRevisionStatus.VALIDATING.value:
        await mark_revision_reviewable(db, revision_id=revision.id)
    elif revision.status == GrammarCanonicalRevisionStatus.REVIEWABLE.value:
        revision.diagnostics_json = {"status": "valid"}
        revision.updated_at = utc_now()
        await db.flush()

    return _revision_result(True, lesson, revision, "valid")


async def inspect_revision(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    include_private_diagnostics: bool = False,
    write_artifact: bool = False,
    write_html_artifact: bool = False,
    artifact_dir: Path | None = None,
) -> WorkflowCommandResult:
    revision = await _load_revision(db, revision_id=revision_id)
    lesson = await _load_lesson(db, lesson_id=revision.lesson_id)
    inspection = build_student_safe_inspection(
        lesson=lesson,
        revision=revision,
        include_private_diagnostics=include_private_diagnostics,
    )
    if write_artifact:
        inspection["review_artifact_ref"] = write_student_safe_review_artifact(
            revision_id=str(revision.id),
            inspection=inspection,
            base_dir=artifact_dir,
        )
    if write_html_artifact:
        inspection["review_html_artifact_ref"] = write_student_safe_review_html_artifact(
            revision_id=str(revision.id),
            inspection=inspection,
            base_dir=artifact_dir,
        )
    return WorkflowCommandResult(ok=True, data=inspection)


async def publish_revision(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
) -> WorkflowCommandResult:
    revision = await _load_revision(db, revision_id=revision_id, for_update=True)
    lesson = await _load_lesson(db, lesson_id=revision.lesson_id)
    if revision.status != GrammarCanonicalRevisionStatus.REVIEWABLE.value:
        raise GrammarCanonicalAuthoringWorkflowError(
            "revision_not_publishable",
            f"Only reviewable revisions can be published; got {revision.status}",
        )

    validation = validate_persisted_revision_payload(
        lesson=lesson,
        revision=revision,
        require_existing_hash=True,
    )
    if not validation.valid:
        await mark_revision_failed(db, revision_id=revision.id, diagnostics_json=validation.diagnostics_json)
        return _revision_result(False, lesson, revision, validation.diagnostics_json.get("code", "validation_failed"))

    previous = await get_active_published_revision_by_lesson_id(db, lesson_id=lesson.id, for_update=True)
    published = await publish_reviewable_revision(db, lesson_id=lesson.id, revision_id=revision.id)
    return WorkflowCommandResult(
        ok=True,
        data={
            "canonical_lesson_id": str(lesson.id),
            "grammar_id": lesson.grammar_id,
            "cefr_level": lesson.cefr_level,
            "locale": lesson.locale,
            "methodology_version": lesson.methodology_version,
            "published_revision_id": str(published.id),
            "revision_number": published.revision_number,
            "content_hash": published.content_hash,
            "previous_revision_archived": str(previous.id) if previous is not None and previous.id != published.id else "",
        },
    )


async def archive_canonical_revision(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
) -> WorkflowCommandResult:
    revision = await archive_revision(db, revision_id=revision_id)
    lesson = await _load_lesson(db, lesson_id=revision.lesson_id)
    return _revision_result(True, lesson, revision, "archived")


async def list_canonical_revisions(
    db: AsyncSession,
    *,
    grammar_id: str | None = None,
    cefr_level: str | None = None,
    locale: str | None = None,
    methodology_version: str | None = None,
    status: str | None = None,
) -> WorkflowCommandResult:
    stmt = select(GrammarCanonicalLessonRevision, GrammarCanonicalLesson).join(
        GrammarCanonicalLesson,
        GrammarCanonicalLesson.id == GrammarCanonicalLessonRevision.lesson_id,
    )
    if grammar_id:
        stmt = stmt.where(GrammarCanonicalLesson.grammar_id == normalize_grammar_id(grammar_id))
    if cefr_level:
        stmt = stmt.where(GrammarCanonicalLesson.cefr_level == cefr_level.upper())
    if locale:
        stmt = stmt.where(GrammarCanonicalLesson.locale == locale)
    if methodology_version:
        stmt = stmt.where(GrammarCanonicalLesson.methodology_version == methodology_version)
    if status:
        stmt = stmt.where(GrammarCanonicalLessonRevision.status == status)
    stmt = stmt.order_by(
        GrammarCanonicalLesson.grammar_id.asc(),
        GrammarCanonicalLesson.cefr_level.asc(),
        GrammarCanonicalLesson.locale.asc(),
        GrammarCanonicalLessonRevision.revision_number.asc(),
    )
    rows = (await db.execute(stmt)).all()
    return WorkflowCommandResult(
        ok=True,
        data={
            "revisions": [
                {
                    "canonical_lesson_id": str(lesson.id),
                    "revision_id": str(revision.id),
                    "grammar_id": lesson.grammar_id,
                    "cefr_level": lesson.cefr_level,
                    "locale": lesson.locale,
                    "methodology_version": lesson.methodology_version,
                    "revision_number": revision.revision_number,
                    "status": revision.status,
                    "schema_version": revision.schema_version,
                    "prompt_version": revision.prompt_version,
                    "catalog_version": revision.catalog_version,
                    "content_hash": revision.content_hash,
                    "generated_at": revision.generated_at.isoformat() if revision.generated_at else None,
                    "published_at": revision.published_at.isoformat() if revision.published_at else None,
                }
                for revision, lesson in rows
            ]
        },
    )


async def retry_failed_revision(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
) -> WorkflowCommandResult:
    source = await _load_revision(db, revision_id=revision_id, for_update=True)
    if source.status not in {
        GrammarCanonicalRevisionStatus.FAILED.value,
        GrammarCanonicalRevisionStatus.GENERATING.value,
    }:
        raise GrammarCanonicalAuthoringWorkflowError(
            "revision_not_retryable",
            f"Only failed or stale generating revisions can be retried; got {source.status}",
        )
    if source.status == GrammarCanonicalRevisionStatus.GENERATING.value:
        await mark_revision_failed(
            db,
            revision_id=source.id,
            diagnostics_json=safe_diagnostics("stale_generating_marked_failed", "Operator retry marked stale generating revision failed"),
        )
    lesson = await _load_lesson(db, lesson_id=source.lesson_id)
    new_revision = await create_next_draft_revision(db, lesson_id=lesson.id)
    return WorkflowCommandResult(
        ok=True,
        data={
            "source_revision_id": str(source.id),
            "source_status": source.status,
            "new_revision_id": str(new_revision.id),
            "new_revision_number": new_revision.revision_number,
            "canonical_lesson_id": str(lesson.id),
            "grammar_id": lesson.grammar_id,
            "cefr_level": lesson.cefr_level,
            "locale": lesson.locale,
            "methodology_version": lesson.methodology_version,
        },
    )


async def _load_revision(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    for_update: bool = False,
) -> GrammarCanonicalLessonRevision:
    revision = await read_revision_by_id(db, revision_id=revision_id, for_update=for_update)
    if revision is None:
        raise GrammarCanonicalAuthoringWorkflowError("revision_not_found", "Revision was not found")
    return revision


async def _load_lesson(
    db: AsyncSession,
    *,
    lesson_id: uuid.UUID,
) -> GrammarCanonicalLesson:
    lesson = await get_canonical_lesson_by_id(db, lesson_id=lesson_id)
    if lesson is None:
        raise GrammarCanonicalAuthoringWorkflowError("canonical_lesson_not_found", "Canonical lesson was not found")
    return lesson


async def _mark_failed_from_any_mutable_state(
    db: AsyncSession,
    revision: GrammarCanonicalLessonRevision,
    diagnostics_json: dict[str, Any],
) -> None:
    if revision.status == GrammarCanonicalRevisionStatus.DRAFT.value:
        await mark_revision_generating(db, revision_id=revision.id)
    if revision.status == GrammarCanonicalRevisionStatus.GENERATING.value:
        await mark_revision_failed(db, revision_id=revision.id, diagnostics_json=diagnostics_json)
    elif revision.status == GrammarCanonicalRevisionStatus.VALIDATING.value:
        await mark_revision_failed(db, revision_id=revision.id, diagnostics_json=diagnostics_json)
    elif revision.status == GrammarCanonicalRevisionStatus.REVIEWABLE.value:
        await mark_revision_failed(db, revision_id=revision.id, diagnostics_json=diagnostics_json)
    elif revision.status == GrammarCanonicalRevisionStatus.FAILED.value:
        revision.diagnostics_json = dict(diagnostics_json)
        revision.updated_at = utc_now()
        await db.flush()


def _raw_or_structured_output(result: CanonicalAuthoringAdapterResult) -> str | dict[str, Any]:
    if result.raw_response_text is not None:
        return result.raw_response_text
    return {
        "student_content": result.student_content_json,
        "server_teaching_metadata": result.server_teaching_metadata_json,
    }


def _write_artifact_if_present(
    revision: GrammarCanonicalLessonRevision,
    result: CanonicalAuthoringAdapterResult,
    *,
    artifact_dir: Path | None,
    success: bool,
) -> str | None:
    return write_raw_authoring_artifact(
        revision_id=str(revision.id),
        raw_response_text=result.raw_response_text,
        success=success,
        base_dir=artifact_dir,
        metadata={
            "provider_id": result.provider_id,
            "authoring_model": result.authoring_model,
            "stop_reason": result.stop_reason,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        },
    )


def _revision_result(
    ok: bool,
    lesson: GrammarCanonicalLesson,
    revision: GrammarCanonicalLessonRevision,
    message: str,
) -> WorkflowCommandResult:
    return WorkflowCommandResult(
        ok=ok,
        message=message,
        data={
            "canonical_lesson_id": str(lesson.id),
            "revision_id": str(revision.id),
            "grammar_id": lesson.grammar_id,
            "cefr_level": lesson.cefr_level,
            "locale": lesson.locale,
            "methodology_version": lesson.methodology_version,
            "revision_number": revision.revision_number,
            "status": revision.status,
            "schema_version": revision.schema_version,
            "prompt_version": revision.prompt_version,
            "catalog_version": revision.catalog_version,
            "content_hash": revision.content_hash,
            "raw_artifact_ref": revision.raw_artifact_ref,
            "diagnostics_code": (revision.diagnostics_json or {}).get("code", ""),
        },
    )
