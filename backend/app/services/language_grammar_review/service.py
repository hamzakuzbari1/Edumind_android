"""Grammar Review service (G2.3) — schedule/queue from mastery + review history."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.services.language_grammar.enums import GrammarReviewMode
from app.services.language_grammar_catalog.catalog import get_default_catalog
from app.services.language_grammar_mastery.storage import (
    mastery_bucket_from_payload,
    snapshot_from_bucket as mastery_snapshot_from_bucket,
)
from app.services.language_grammar_mastery.types import GrammarMasterySnapshot
from app.services.language_grammar_review.engine import (
    GrammarReviewError,
    compute_review_snapshot,
    disabled_review_snapshot,
    empty_student_state,
    format_ts,
    record_review_completed,
)
from app.services.language_grammar_review.flags import (
    grammar_engine_enabled,
    grammar_engine_select_enabled,
)
from app.services.language_grammar_review.locking import lock_grammar_review_row
from app.services.language_grammar_review.storage import (
    bucket_from_student_state,
    merge_review_into_payload,
    review_bucket_from_payload,
    student_state_from_bucket,
)
from app.services.language_grammar_review.types import (
    GrammarReviewQueue,
    GrammarReviewSnapshot,
    GrammarReviewStudentState,
)
from app.services.language_progression_service import ensure_progression_row


def _now_iso() -> str:
    return format_ts(datetime.now(timezone.utc))


def compute_from_mastery(
    *,
    mastery: GrammarMasterySnapshot,
    student: GrammarReviewStudentState | None = None,
    as_of: str | datetime | None = None,
) -> GrammarReviewSnapshot:
    """Pure compute path. Respects ENABLED flag. Never mutates Progression."""
    as_of_value = as_of if as_of is not None else _now_iso()
    if not grammar_engine_enabled():
        as_of_str = format_ts(as_of_value) if isinstance(as_of_value, datetime) else str(as_of_value)
        return disabled_review_snapshot(
            student_id=mastery.student_id,
            language_id=mastery.language_id,
            as_of=as_of_str,
        )

    state = student or empty_student_state(
        student_id=mastery.student_id,
        language_id=mastery.language_id,
    )
    if state.student_id != mastery.student_id or state.language_id != mastery.language_id:
        raise GrammarReviewError("Review student state mismatch")

    catalog = get_default_catalog()
    return compute_review_snapshot(
        mastery=mastery,
        student=state,
        catalog=catalog,
        as_of=as_of_value,
    )


def selection_queue_or_empty(snapshot: GrammarReviewSnapshot) -> GrammarReviewQueue:
    """When SELECT is off, hide authoritative queue for skill consumption."""
    if not snapshot.enabled:
        return GrammarReviewQueue()
    if not grammar_engine_select_enabled():
        return GrammarReviewQueue()
    return snapshot.queue


async def evaluate_review_queue(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    as_of: str | datetime | None = None,
) -> GrammarReviewSnapshot:
    """Load mastery + review history, compute schedule/queue (history unchanged)."""
    as_of_value = as_of if as_of is not None else _now_iso()
    if not grammar_engine_enabled():
        as_of_str = format_ts(as_of_value) if isinstance(as_of_value, datetime) else str(as_of_value)
        return disabled_review_snapshot(
            student_id=student_id,
            language_id=language_id,
            as_of=as_of_str,
        )

    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    row = await lock_grammar_review_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        mastery = GrammarMasterySnapshot(student_id=student_id, language_id=language_id)
        return compute_from_mastery(mastery=mastery, as_of=as_of_value)

    payload = dict(row.promotion_readiness_json or {})
    mastery = mastery_snapshot_from_bucket(
        mastery_bucket_from_payload(payload),
        student_id=student_id,
        language_id=language_id,
    )
    student = student_state_from_bucket(
        review_bucket_from_payload(payload),
        student_id=student_id,
        language_id=language_id,
    )
    return compute_from_mastery(mastery=mastery, student=student, as_of=as_of_value)


async def complete_review_and_persist(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    grammar_id: str,
    reviewed_at: str | datetime | None = None,
    mode: GrammarReviewMode = GrammarReviewMode.spaced_practice,
) -> GrammarReviewStudentState:
    """Record a completed review into durable history. Does not unlock or progress topics."""
    if not grammar_engine_enabled():
        return empty_student_state(student_id=student_id, language_id=language_id)

    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    row = await lock_grammar_review_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise GrammarReviewError("Progression row unavailable for review persistence")

    payload = dict(row.promotion_readiness_json or {})
    state = student_state_from_bucket(
        review_bucket_from_payload(payload),
        student_id=student_id,
        language_id=language_id,
    )
    catalog = get_default_catalog()
    updated = record_review_completed(
        state,
        grammar_id=grammar_id,
        reviewed_at=reviewed_at if reviewed_at is not None else _now_iso(),
        mode=mode,
        catalog=catalog,
    )
    row.promotion_readiness_json = merge_review_into_payload(
        payload, bucket_from_student_state(updated)
    )
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return updated


async def get_review_student_state(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
) -> GrammarReviewStudentState:
    if not grammar_engine_enabled():
        return empty_student_state(student_id=student_id, language_id=language_id)
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    row = await lock_grammar_review_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        return empty_student_state(student_id=student_id, language_id=language_id)
    return student_state_from_bucket(
        review_bucket_from_payload(dict(row.promotion_readiness_json or {})),
        student_id=student_id,
        language_id=language_id,
    )
