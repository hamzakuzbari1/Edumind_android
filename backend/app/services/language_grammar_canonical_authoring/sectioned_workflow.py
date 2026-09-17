"""Blueprint-driven sectioned canonical grammar authoring workflow."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.grammar_canonical_lesson import (
    GrammarCanonicalLesson,
    GrammarCanonicalLessonRevision,
    GrammarCanonicalLessonRevisionUnitAttempt,
)
from app.services.language_grammar_canonical_authoring.errors import (
    GrammarCanonicalAuthoringWorkflowError,
)
from app.services.language_grammar_canonical_authoring.section_assembly import (
    REQUIRED_ACCEPTED_UNITS,
    assemble_canonical_lesson_from_units,
)
from app.services.language_grammar_canonical_authoring.section_validation import (
    validate_blueprint_unit,
    validate_sectioned_unit,
)
from app.services.language_grammar_canonical_authoring.types import (
    CanonicalAuthoringAdapterRequest,
    CanonicalLessonIdentityInput,
    DEFAULT_CATALOG_VERSION,
    DEFAULT_PROMPT_VERSION,
    DEFAULT_SCHEMA_VERSION,
    LEARNER_UNIT_KEYS,
    SectionedAuthoringUnitResult,
    SectionedCanonicalAuthoringAdapter,
    WorkflowCommandResult,
)
from app.services.language_grammar_canonical_authoring.unit_repository import (
    accept_unit_attempt,
    create_next_unit_attempt,
    get_accepted_unit_attempt,
    get_unit_attempt,
    list_unit_attempts,
    mark_unit_attempt_failed,
    mark_unit_attempt_generating,
    supersede_accepted_unit_attempt,
)
from app.services.language_grammar_canonical_authoring.validation import (
    safe_diagnostics,
    validation_summary,
)
from app.services.language_grammar_canonical_authoring.workflow import (
    _load_lesson,
    _load_revision,
    _revision_result,
    ensure_identity,
    normalize_identity_input,
    utc_now,
)
from app.services.language_grammar_canonical_authoring.artifacts import write_raw_authoring_artifact
from app.services.language_grammar_canonical_authoring.blueprint_compaction import (
    is_compact_blueprint_plan,
    normalize_compact_blueprint_plan,
    validate_compact_blueprint_plan,
)
from app.services.language_grammar_canonical_lessons import (
    GrammarCanonicalRevisionStatus,
    create_next_draft_revision,
    mark_revision_failed,
    mark_revision_generating,
    mark_revision_reviewable,
    mark_revision_status,
    mark_revision_validating,
    store_or_update_draft_content,
)
from app.services.language_grammar_pipeline.stages import _grammar_authoring_profile


async def generate_sectioned_draft_revision(
    db: AsyncSession,
    *,
    identity: CanonicalLessonIdentityInput,
    adapter: SectionedCanonicalAuthoringAdapter,
    artifact_dir: Path | None = None,
) -> WorkflowCommandResult:
    identity_result = await ensure_identity(db, identity)
    lesson = await _load_lesson(db, lesson_id=uuid.UUID(identity_result.data["canonical_lesson_id"]))
    revision = await create_next_draft_revision(db, lesson_id=lesson.id)
    await mark_revision_generating(db, revision_id=revision.id)
    request = _request_for_lesson(lesson)

    accepted: dict[str, GrammarCanonicalLessonRevisionUnitAttempt] = {}
    blueprint_result = await _generate_and_validate_unit(
        db,
        lesson=lesson,
        revision=revision,
        adapter=adapter,
        request=request,
        unit_key="blueprint",
        blueprint=None,
        accepted_prior_units={},
        artifact_dir=artifact_dir,
    )
    if not blueprint_result.ok:
        await mark_revision_failed(db, revision_id=revision.id, diagnostics_json={"code": "blueprint_failed"})
        return _sectioned_result(False, lesson, revision, "blueprint_failed")
    accepted["blueprint"] = await _accepted_or_raise(db, revision_id=revision.id, unit_key="blueprint")
    blueprint = accepted["blueprint"].blueprint_json or {}

    prior_payloads: dict[str, dict[str, Any]] = {}
    for unit_key in LEARNER_UNIT_KEYS:
        result = await _generate_and_validate_unit(
            db,
            lesson=lesson,
            revision=revision,
            adapter=adapter,
            request=request,
            unit_key=unit_key,
            blueprint=blueprint,
            accepted_prior_units=prior_payloads,
            artifact_dir=artifact_dir,
        )
        if not result.ok:
            await mark_revision_failed(
                db,
                revision_id=revision.id,
                diagnostics_json={"code": f"{unit_key}_failed", "unit_key": unit_key},
            )
            return _sectioned_result(False, lesson, revision, f"{unit_key}_failed")
        accepted[unit_key] = await _accepted_or_raise(db, revision_id=revision.id, unit_key=unit_key)
        prior_payloads[unit_key] = accepted[unit_key].public_payload_json or {}

    return await assemble_sectioned_revision(db, revision_id=revision.id)


async def assemble_sectioned_revision(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
) -> WorkflowCommandResult:
    revision = await _load_revision(db, revision_id=revision_id, for_update=True)
    lesson = await _load_lesson(db, lesson_id=revision.lesson_id)
    if revision.status in {
        GrammarCanonicalRevisionStatus.PUBLISHED.value,
        GrammarCanonicalRevisionStatus.ARCHIVED.value,
    }:
        raise GrammarCanonicalAuthoringWorkflowError("revision_not_mutable", "Published/archived revisions cannot be assembled")
    await _ensure_parent_ready_for_validation(db, revision)
    accepted = await _accepted_attempts(db, revision_id=revision.id)
    assembled = assemble_canonical_lesson_from_units(lesson=lesson, accepted_attempts=accepted)
    if not assembled.valid:
        await mark_revision_failed(db, revision_id=revision.id, diagnostics_json=assembled.diagnostics_json)
        return _revision_result(False, lesson, revision, assembled.diagnostics_json.get("code", "assembly_failed"))
    stored = await store_or_update_draft_content(
        db,
        revision_id=revision.id,
        student_content_json=assembled.normalized_student_content or {},
        server_teaching_metadata_json=assembled.normalized_server_teaching_metadata or {},
        schema_version=DEFAULT_SCHEMA_VERSION,
        prompt_version="sectioned_assembly",
        catalog_version=DEFAULT_CATALOG_VERSION,
        authoring_provider="sectioned",
        authoring_model="assembled",
        diagnostics_json={"status": "valid", "source": "sectioned_assembly"},
        generated_at=utc_now(),
    )
    await mark_revision_reviewable(db, revision_id=stored.id)
    return _sectioned_result(True, lesson, stored, "reviewable")


async def list_revision_unit_attempts(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    unit_key: str | None = None,
) -> WorkflowCommandResult:
    attempts = await list_unit_attempts(db, revision_id=revision_id, unit_key=unit_key)
    return WorkflowCommandResult(
        ok=True,
        data={
            "revision_id": str(revision_id),
            "unit_attempts": [_unit_attempt_summary(attempt) for attempt in attempts],
        },
    )


async def inspect_unit_attempt(
    db: AsyncSession,
    *,
    attempt_id: uuid.UUID,
    include_private_diagnostics: bool = False,
) -> WorkflowCommandResult:
    attempt = await get_unit_attempt(db, attempt_id=attempt_id)
    if attempt is None:
        raise GrammarCanonicalAuthoringWorkflowError("unit_attempt_not_found", "Unit attempt was not found")
    data: dict[str, Any] = {
        "unit_attempt": _unit_attempt_summary(attempt),
        "validation_summary": validation_summary(attempt.diagnostics_json),
    }
    if attempt.unit_key == "blueprint":
        blueprint = attempt.blueprint_json or {}
        data["blueprint_summary"] = {
            "grammar_target": blueprint.get("grammar_target"),
            "display_name": blueprint.get("display_name"),
            "core_communicative_meaning": blueprint.get("core_communicative_meaning"),
            "required_forms": blueprint.get("required_forms"),
            "production_goal": blueprint.get("production_goal"),
        }
    else:
        data["public_payload"] = attempt.public_payload_json or {}
    if include_private_diagnostics:
        data["private_diagnostics"] = validation_summary(attempt.diagnostics_json)
    return WorkflowCommandResult(ok=True, data=data)


async def retry_unit_attempt(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    unit_key: str,
    adapter: SectionedCanonicalAuthoringAdapter,
    supersede_accepted: bool = False,
    artifact_dir: Path | None = None,
) -> WorkflowCommandResult:
    revision = await _load_revision(db, revision_id=revision_id, for_update=True)
    lesson = await _load_lesson(db, lesson_id=revision.lesson_id)
    if revision.status in {
        GrammarCanonicalRevisionStatus.PUBLISHED.value,
        GrammarCanonicalRevisionStatus.ARCHIVED.value,
        GrammarCanonicalRevisionStatus.REVIEWABLE.value,
    } and not supersede_accepted:
        raise GrammarCanonicalAuthoringWorkflowError("revision_not_retryable", "Use a new revision to change reviewable/published content")
    existing = await get_accepted_unit_attempt(db, revision_id=revision.id, unit_key=unit_key)
    if existing is not None:
        if not supersede_accepted:
            raise GrammarCanonicalAuthoringWorkflowError("accepted_unit_exists", "Accepted unit requires explicit supersede")
        await supersede_accepted_unit_attempt(db, attempt=existing)

    blueprint_attempt = await get_accepted_unit_attempt(db, revision_id=revision.id, unit_key="blueprint")
    if unit_key != "blueprint" and blueprint_attempt is None:
        raise GrammarCanonicalAuthoringWorkflowError("missing_blueprint", "Cannot retry learner unit without accepted blueprint")
    if unit_key != "blueprint" and blueprint_attempt is not None:
        compatibility = validate_blueprint_unit(blueprint_attempt.blueprint_json or {}, lesson=lesson)
        if not compatibility.valid:
            return WorkflowCommandResult(
                ok=False,
                data={
                    "revision_id": str(revision.id),
                    "unit_key": unit_key,
                    "diagnostics": compatibility.diagnostics_json,
                },
                message=compatibility.diagnostics_json.get("code", "blueprint_incompatible"),
            )
    request = _request_for_lesson(lesson)
    result = await _generate_and_validate_unit(
        db,
        lesson=lesson,
        revision=revision,
        adapter=adapter,
        request=request,
        unit_key=unit_key,
        blueprint=blueprint_attempt.blueprint_json if blueprint_attempt else None,
        accepted_prior_units=await _prior_public_payloads(db, revision.id),
        artifact_dir=artifact_dir,
    )
    if result.ok and unit_key == "blueprint" and revision.status == GrammarCanonicalRevisionStatus.FAILED.value:
        await mark_revision_status(db, revision_id=revision.id, status=GrammarCanonicalRevisionStatus.DRAFT)
        await mark_revision_generating(db, revision_id=revision.id)
    return result


async def supersede_unit_attempt(
    db: AsyncSession,
    *,
    attempt_id: uuid.UUID,
) -> WorkflowCommandResult:
    attempt = await get_unit_attempt(db, attempt_id=attempt_id, for_update=True)
    if attempt is None:
        raise GrammarCanonicalAuthoringWorkflowError("unit_attempt_not_found", "Unit attempt was not found")
    await supersede_accepted_unit_attempt(db, attempt=attempt)
    return WorkflowCommandResult(ok=True, data=_unit_attempt_summary(attempt), message="superseded")


async def _generate_and_validate_unit(
    db: AsyncSession,
    *,
    lesson: GrammarCanonicalLesson,
    revision: GrammarCanonicalLessonRevision,
    adapter: SectionedCanonicalAuthoringAdapter,
    request: CanonicalAuthoringAdapterRequest,
    unit_key: str,
    blueprint: dict[str, Any] | None,
    accepted_prior_units: dict[str, dict[str, Any]],
    artifact_dir: Path | None,
) -> WorkflowCommandResult:
    attempt = await create_next_unit_attempt(db, revision_id=revision.id, unit_key=unit_key)
    await mark_unit_attempt_generating(db, attempt=attempt, provider="pending", model="pending", prompt_version=DEFAULT_PROMPT_VERSION)
    try:
        result = (
            adapter.generate_blueprint(request)
            if unit_key == "blueprint"
            else adapter.generate_unit(unit_key, blueprint or {}, accepted_prior_units, request)
        )
    except Exception as exc:  # noqa: BLE001
        await mark_unit_attempt_failed(
            db,
            attempt=attempt,
            diagnostics_json=safe_diagnostics("provider_failure", str(exc)),
        )
        return _unit_result(False, attempt, "provider_failure")

    raw_ref = _write_unit_artifact(attempt, result, artifact_dir=artifact_dir)
    if not result.success:
        attempt.provider = result.provider_id
        attempt.model = result.authoring_model
        attempt.prompt_version = result.prompt_version
        attempt.raw_artifact_ref = raw_ref or result.raw_artifact_ref
        attempt.stop_reason = result.stop_reason
        attempt.input_tokens = result.input_tokens
        attempt.output_tokens = result.output_tokens
        attempt.truncated = result.truncated
        await mark_unit_attempt_failed(
            db,
            attempt=attempt,
            diagnostics_json=dict(result.diagnostics_json or safe_diagnostics("provider_failure", "Provider failed")),
        )
        return _unit_result(False, attempt, "provider_failure")

    payload = dict(result.structured_payload or {})
    if unit_key == "blueprint" and is_compact_blueprint_plan(payload):
        compact_diagnostics = validate_compact_blueprint_plan(
            payload,
            lesson=lesson,
            grammar_profile=request.grammar_profile,
        )
        if compact_diagnostics.get("status") != "valid":
            attempt.blueprint_json = payload
            attempt.provider = result.provider_id
            attempt.model = result.authoring_model
            attempt.prompt_version = result.prompt_version
            attempt.raw_artifact_ref = raw_ref or result.raw_artifact_ref
            attempt.stop_reason = result.stop_reason
            attempt.input_tokens = result.input_tokens
            attempt.output_tokens = result.output_tokens
            attempt.truncated = result.truncated
            await mark_unit_attempt_failed(
                db,
                attempt=attempt,
                diagnostics_json=_merge_unit_diagnostics(result, compact_diagnostics, validation_passed=False),
            )
            return _unit_result(False, attempt, compact_diagnostics.get("code", "compact_blueprint_invalid"))
        payload = normalize_compact_blueprint_plan(
            payload,
            lesson=lesson,
            grammar_profile=request.grammar_profile,
        )
    validation = validate_sectioned_unit(
        unit_key,
        payload,
        result.private_metadata_json,
        blueprint=blueprint,
        lesson=lesson,
    )
    if not validation.valid:
        attempt.public_payload_json = payload if unit_key != "blueprint" else None
        attempt.blueprint_json = payload if unit_key == "blueprint" else None
        attempt.private_metadata_json = result.private_metadata_json
        attempt.provider = result.provider_id
        attempt.model = result.authoring_model
        attempt.prompt_version = result.prompt_version
        attempt.raw_artifact_ref = raw_ref or result.raw_artifact_ref
        attempt.stop_reason = result.stop_reason
        attempt.input_tokens = result.input_tokens
        attempt.output_tokens = result.output_tokens
        attempt.truncated = result.truncated
        await mark_unit_attempt_failed(
            db,
            attempt=attempt,
            diagnostics_json=_merge_unit_diagnostics(result, validation.diagnostics_json, validation_passed=False),
        )
        return _unit_result(False, attempt, validation.diagnostics_json.get("code", "unit_invalid"))

    await accept_unit_attempt(
        db,
        attempt=attempt,
        public_payload_json=validation.normalized_public_payload,
        private_metadata_json=validation.normalized_private_metadata,
        blueprint_json=validation.normalized_blueprint,
        provider=result.provider_id,
        model=result.authoring_model,
        prompt_version=result.prompt_version,
        stop_reason=result.stop_reason,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        truncated=result.truncated,
        diagnostics_json=_merge_unit_diagnostics(result, validation.diagnostics_json, validation_passed=True),
        raw_artifact_ref=raw_ref or result.raw_artifact_ref,
        generated_at=result.generated_at,
    )
    return _unit_result(True, attempt, "accepted")


async def _ensure_parent_ready_for_validation(
    db: AsyncSession,
    revision: GrammarCanonicalLessonRevision,
) -> None:
    if revision.status == GrammarCanonicalRevisionStatus.FAILED.value:
        await mark_revision_status(db, revision_id=revision.id, status=GrammarCanonicalRevisionStatus.DRAFT)
    if revision.status == GrammarCanonicalRevisionStatus.DRAFT.value:
        await mark_revision_generating(db, revision_id=revision.id)
    if revision.status == GrammarCanonicalRevisionStatus.GENERATING.value:
        await mark_revision_validating(db, revision_id=revision.id)


async def _accepted_attempts(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
) -> dict[str, GrammarCanonicalLessonRevisionUnitAttempt]:
    out: dict[str, GrammarCanonicalLessonRevisionUnitAttempt] = {}
    for unit_key in REQUIRED_ACCEPTED_UNITS:
        attempt = await get_accepted_unit_attempt(db, revision_id=revision_id, unit_key=unit_key)
        if attempt is not None:
            out[unit_key] = attempt
    return out


async def _accepted_or_raise(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    unit_key: str,
) -> GrammarCanonicalLessonRevisionUnitAttempt:
    attempt = await get_accepted_unit_attempt(db, revision_id=revision_id, unit_key=unit_key)
    if attempt is None:
        raise GrammarCanonicalAuthoringWorkflowError("accepted_unit_missing", f"Accepted unit missing: {unit_key}")
    return attempt


async def _prior_public_payloads(db: AsyncSession, revision_id: uuid.UUID) -> dict[str, dict[str, Any]]:
    attempts = await list_unit_attempts(db, revision_id=revision_id)
    return {
        attempt.unit_key: dict(attempt.public_payload_json or attempt.blueprint_json or {})
        for attempt in attempts
        if attempt.status == "accepted"
    }


def _request_for_lesson(lesson: GrammarCanonicalLesson) -> CanonicalAuthoringAdapterRequest:
    profile = _grammar_authoring_profile((lesson.grammar_id,))
    return CanonicalAuthoringAdapterRequest(
        grammar_id=lesson.grammar_id,
        display_name=str(profile.get("display_name") or lesson.grammar_id),
        cefr_level=lesson.cefr_level,
        locale=lesson.locale,
        methodology_version=lesson.methodology_version,
        schema_version=DEFAULT_SCHEMA_VERSION,
        prompt_version=DEFAULT_PROMPT_VERSION,
        catalog_version=DEFAULT_CATALOG_VERSION,
        grammar_profile=profile,
        learner_signals={"source": "offline_sectioned_authoring", "synthetic": True},
    )


def _write_unit_artifact(
    attempt: GrammarCanonicalLessonRevisionUnitAttempt,
    result: SectionedAuthoringUnitResult,
    *,
    artifact_dir: Path | None,
) -> str | None:
    return write_raw_authoring_artifact(
        revision_id=f"{attempt.revision_id}-{attempt.unit_key}-{attempt.attempt_number}",
        raw_response_text=result.raw_response_text,
        success=result.success,
        base_dir=artifact_dir,
        metadata={
            "unit_key": attempt.unit_key,
            "attempt_number": attempt.attempt_number,
            "provider_id": result.provider_id,
            "authoring_model": result.authoring_model,
            "stop_reason": result.stop_reason,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "truncated": result.truncated,
        },
    )


def _unit_attempt_summary(attempt: GrammarCanonicalLessonRevisionUnitAttempt) -> dict[str, Any]:
    return {
        "attempt_id": str(attempt.id),
        "revision_id": str(attempt.revision_id),
        "unit_key": attempt.unit_key,
        "attempt_number": attempt.attempt_number,
        "status": attempt.status,
        "content_hash": attempt.content_hash,
        "provider": attempt.provider,
        "model": attempt.model,
        "prompt_version": attempt.prompt_version,
        "stop_reason": attempt.stop_reason,
        "input_tokens": attempt.input_tokens,
        "output_tokens": attempt.output_tokens,
        "truncated": attempt.truncated,
        "generated_at": attempt.generated_at.isoformat() if attempt.generated_at else None,
        "validated_at": attempt.validated_at.isoformat() if attempt.validated_at else None,
        "accepted_at": attempt.accepted_at.isoformat() if attempt.accepted_at else None,
        "diagnostics": validation_summary(attempt.diagnostics_json),
    }


def _merge_unit_diagnostics(
    result: SectionedAuthoringUnitResult,
    validation_diagnostics: dict[str, Any],
    *,
    validation_passed: bool,
) -> dict[str, Any]:
    out = dict(validation_diagnostics or {})
    out["json_parse_passed"] = result.json_parse_passed
    out["validation_passed"] = validation_passed
    out["provider_stop_reason"] = result.stop_reason
    out["truncated"] = result.truncated
    provider_diag = dict(result.diagnostics_json or {})
    if provider_diag:
        out["provider_diagnostics"] = {
            key: provider_diag.get(key)
            for key in (
                "unit_key",
                "provider",
                "model",
                "stop_reason",
                "input_tokens",
                "output_tokens",
                "truncated",
                "prompt_version",
                "parse_stage",
                "top_level_keys",
            )
            if key in provider_diag
        }
    return out


def _unit_result(
    ok: bool,
    attempt: GrammarCanonicalLessonRevisionUnitAttempt,
    message: str,
) -> WorkflowCommandResult:
    return WorkflowCommandResult(ok=ok, message=message, data=_unit_attempt_summary(attempt))


def _sectioned_result(
    ok: bool,
    lesson: GrammarCanonicalLesson,
    revision: GrammarCanonicalLessonRevision,
    message: str,
) -> WorkflowCommandResult:
    result = _revision_result(ok, lesson, revision, message)
    data = dict(result.data)
    data["generation_mode"] = "sectioned_canonical_grammar_lesson_authoring"
    return WorkflowCommandResult(ok=ok, message=message, data=data)
