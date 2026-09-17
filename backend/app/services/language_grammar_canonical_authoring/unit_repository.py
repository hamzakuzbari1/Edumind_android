"""Repository helpers for sectioned canonical lesson unit attempts."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.grammar_canonical_lesson import (
    GRAMMAR_CANONICAL_UNIT_ATTEMPT_STATUSES,
    GRAMMAR_CANONICAL_UNIT_KEYS,
    GrammarCanonicalLessonRevision,
    GrammarCanonicalLessonRevisionUnitAttempt,
)
from app.services.language_grammar_canonical_authoring.errors import (
    GrammarCanonicalAuthoringWorkflowError,
)

ACCEPTED_UNIT_STATUS = "accepted"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compute_unit_attempt_hash(
    *,
    unit_key: str,
    public_payload_json: dict[str, Any] | None = None,
    private_metadata_json: dict[str, Any] | None = None,
    blueprint_json: dict[str, Any] | None = None,
) -> str:
    payload = {
        "blueprint_json": blueprint_json,
        "private_metadata_json": private_metadata_json,
        "public_payload_json": public_payload_json,
        "unit_key": unit_key,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def create_next_unit_attempt(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    unit_key: str,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevisionUnitAttempt:
    _validate_unit_key(unit_key)
    revision = await db.get(GrammarCanonicalLessonRevision, revision_id)
    if revision is None:
        raise GrammarCanonicalAuthoringWorkflowError("revision_not_found", "Parent revision was not found")
    result = await db.execute(
        select(func.max(GrammarCanonicalLessonRevisionUnitAttempt.attempt_number)).where(
            GrammarCanonicalLessonRevisionUnitAttempt.revision_id == revision_id,
            GrammarCanonicalLessonRevisionUnitAttempt.unit_key == unit_key,
        )
    )
    attempt_number = int(result.scalar_one_or_none() or 0) + 1
    ts = now or utc_now()
    attempt = GrammarCanonicalLessonRevisionUnitAttempt(
        id=uuid.uuid4(),
        revision_id=revision_id,
        unit_key=unit_key,
        attempt_number=attempt_number,
        status="pending",
        created_at=ts,
        updated_at=ts,
    )
    db.add(attempt)
    await db.flush()
    return attempt


async def get_unit_attempt(
    db: AsyncSession,
    *,
    attempt_id: uuid.UUID,
    for_update: bool = False,
) -> GrammarCanonicalLessonRevisionUnitAttempt | None:
    stmt = select(GrammarCanonicalLessonRevisionUnitAttempt).where(
        GrammarCanonicalLessonRevisionUnitAttempt.id == attempt_id
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_unit_attempts(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    unit_key: str | None = None,
) -> list[GrammarCanonicalLessonRevisionUnitAttempt]:
    stmt = select(GrammarCanonicalLessonRevisionUnitAttempt).where(
        GrammarCanonicalLessonRevisionUnitAttempt.revision_id == revision_id
    )
    if unit_key:
        _validate_unit_key(unit_key)
        stmt = stmt.where(GrammarCanonicalLessonRevisionUnitAttempt.unit_key == unit_key)
    stmt = stmt.order_by(
        GrammarCanonicalLessonRevisionUnitAttempt.unit_key.asc(),
        GrammarCanonicalLessonRevisionUnitAttempt.attempt_number.asc(),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_accepted_unit_attempt(
    db: AsyncSession,
    *,
    revision_id: uuid.UUID,
    unit_key: str,
) -> GrammarCanonicalLessonRevisionUnitAttempt | None:
    _validate_unit_key(unit_key)
    result = await db.execute(
        select(GrammarCanonicalLessonRevisionUnitAttempt).where(
            GrammarCanonicalLessonRevisionUnitAttempt.revision_id == revision_id,
            GrammarCanonicalLessonRevisionUnitAttempt.unit_key == unit_key,
            GrammarCanonicalLessonRevisionUnitAttempt.status == ACCEPTED_UNIT_STATUS,
        )
    )
    return result.scalar_one_or_none()


async def mark_unit_attempt_generating(
    db: AsyncSession,
    *,
    attempt: GrammarCanonicalLessonRevisionUnitAttempt,
    provider: str | None = None,
    model: str | None = None,
    prompt_version: str | None = None,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevisionUnitAttempt:
    _assert_status(attempt.status, {"pending"})
    ts = now or utc_now()
    attempt.status = "generating"
    attempt.provider = provider
    attempt.model = model
    attempt.prompt_version = prompt_version
    attempt.updated_at = ts
    await db.flush()
    return attempt


async def mark_unit_attempt_failed(
    db: AsyncSession,
    *,
    attempt: GrammarCanonicalLessonRevisionUnitAttempt,
    diagnostics_json: dict[str, Any],
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevisionUnitAttempt:
    _assert_status(attempt.status, {"pending", "generating", "validating"})
    ts = now or utc_now()
    attempt.status = "failed"
    attempt.diagnostics_json = dict(diagnostics_json)
    attempt.validated_at = ts
    attempt.updated_at = ts
    await db.flush()
    return attempt


async def accept_unit_attempt(
    db: AsyncSession,
    *,
    attempt: GrammarCanonicalLessonRevisionUnitAttempt,
    public_payload_json: dict[str, Any] | None,
    private_metadata_json: dict[str, Any] | None,
    blueprint_json: dict[str, Any] | None,
    provider: str,
    model: str,
    prompt_version: str,
    stop_reason: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    truncated: bool | None = None,
    diagnostics_json: dict[str, Any] | None = None,
    raw_artifact_ref: str | None = None,
    generated_at: datetime | None = None,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevisionUnitAttempt:
    _assert_status(attempt.status, {"pending", "generating", "validating"})
    ts = now or utc_now()
    attempt.status = "validating"
    attempt.public_payload_json = dict(public_payload_json) if public_payload_json is not None else None
    attempt.private_metadata_json = dict(private_metadata_json) if private_metadata_json is not None else None
    attempt.blueprint_json = dict(blueprint_json) if blueprint_json is not None else None
    attempt.provider = provider
    attempt.model = model
    attempt.prompt_version = prompt_version
    attempt.stop_reason = stop_reason
    attempt.input_tokens = input_tokens
    attempt.output_tokens = output_tokens
    attempt.truncated = truncated
    attempt.diagnostics_json = dict(diagnostics_json or {"status": "valid"})
    attempt.raw_artifact_ref = raw_artifact_ref
    attempt.generated_at = generated_at or ts
    attempt.validated_at = ts
    attempt.content_hash = compute_unit_attempt_hash(
        unit_key=attempt.unit_key,
        public_payload_json=attempt.public_payload_json,
        private_metadata_json=attempt.private_metadata_json,
        blueprint_json=attempt.blueprint_json,
    )
    attempt.status = ACCEPTED_UNIT_STATUS
    attempt.accepted_at = ts
    attempt.updated_at = ts
    await db.flush()
    return attempt


async def supersede_accepted_unit_attempt(
    db: AsyncSession,
    *,
    attempt: GrammarCanonicalLessonRevisionUnitAttempt,
    now: datetime | None = None,
) -> GrammarCanonicalLessonRevisionUnitAttempt:
    if attempt.status != ACCEPTED_UNIT_STATUS:
        raise GrammarCanonicalAuthoringWorkflowError("unit_not_accepted", "Only accepted unit attempts can be superseded")
    ts = now or utc_now()
    attempt.status = "superseded"
    attempt.updated_at = ts
    await db.flush()
    return attempt


def _validate_unit_key(unit_key: str) -> None:
    if unit_key not in GRAMMAR_CANONICAL_UNIT_KEYS:
        raise GrammarCanonicalAuthoringWorkflowError("invalid_unit_key", f"Unsupported unit_key: {unit_key}")


def _assert_status(current: str, allowed: set[str]) -> None:
    if current not in GRAMMAR_CANONICAL_UNIT_ATTEMPT_STATUSES or current not in allowed:
        raise GrammarCanonicalAuthoringWorkflowError(
            "invalid_unit_attempt_status",
            f"Cannot mutate unit attempt while status is {current!r}",
        )
