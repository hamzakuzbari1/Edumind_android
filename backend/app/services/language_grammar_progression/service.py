"""Grammar Progression service (G2.1 + patch) — flags, CEFR, storage, engine."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.enums import LanguageLevel
from app.services.language_grammar.enums import GrammarCEFRBand
from app.services.language_grammar_catalog.catalog import get_default_catalog
from app.services.language_grammar_progression.engine import (
    GrammarProgressionError,
    compute_progression_snapshot,
    disabled_snapshot,
)
from app.services.language_grammar_progression.flags import (
    grammar_engine_enabled,
    grammar_engine_select_enabled,
)
from app.services.language_grammar_progression.legacy import normalize_id_set, normalize_to_grammar_id
from app.services.language_grammar_progression.locking import lock_grammar_progression_row
from app.services.language_grammar_progression.storage import (
    apply_snapshot_unlocks_to_state,
    bucket_from_student_state,
    merge_progression_into_payload,
    progression_bucket_from_payload,
    student_state_from_bucket,
)
from app.services.language_grammar_progression.types import (
    GrammarProgressionSnapshot,
    GrammarProgressionStudentState,
)
from app.services.language_progression_service import (
    ensure_progression_row,
    get_official_overall_cefr,
)


def _level_to_band(level: LanguageLevel | str) -> GrammarCEFRBand:
    value = level.value if isinstance(level, LanguageLevel) else str(level)
    return GrammarCEFRBand(value.upper())


def compute_from_state(
    *,
    anchor_cefr: GrammarCEFRBand,
    student: GrammarProgressionStudentState,
) -> GrammarProgressionSnapshot:
    """Pure compute path (tests / callers with explicit anchor). Respects ENABLED flag."""
    if not grammar_engine_enabled():
        return disabled_snapshot(anchor_cefr=anchor_cefr)
    catalog = get_default_catalog()
    normalized = GrammarProgressionStudentState(
        student_id=student.student_id,
        language_id=student.language_id,
        completed_ids=normalize_id_set(student.completed_ids),
        unlocked_ids=normalize_id_set(student.unlocked_ids),
        current_grammar_id=(
            normalize_to_grammar_id(student.current_grammar_id)
            if student.current_grammar_id
            else None
        ),
        stretch_allowed=bool(student.stretch_allowed),
    )
    return compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=anchor_cefr,
        student=normalized,
    )


def selection_snapshot_or_disabled(
    snapshot: GrammarProgressionSnapshot,
) -> GrammarProgressionSnapshot:
    """When SELECT is off, hide authoritative current/next for skill consumption."""
    if snapshot.enabled and grammar_engine_select_enabled():
        return snapshot
    if not snapshot.enabled:
        return snapshot
    return GrammarProgressionSnapshot(
        anchor_cefr=snapshot.anchor_cefr,
        current_grammar_id=None,
        next_grammar_id=None,
        unlocked_ids=snapshot.unlocked_ids,
        locked_ids=snapshot.locked_ids,
        future_ids=snapshot.future_ids,
        stretch_ids=snapshot.stretch_ids,
        candidate_pool_ids=snapshot.candidate_pool_ids,
        candidate_priorities=snapshot.candidate_priorities,
        progression_reason=snapshot.progression_reason
        + ("flag:LANG_GRAMMAR_ENGINE_SELECT=false",),
        stretch_allowed=snapshot.stretch_allowed,
        enabled=True,
    )


async def evaluate_and_persist_grammar_progression(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    stretch_allowed: bool | None = None,
) -> GrammarProgressionSnapshot:
    """Load official overall CEFR + student snapshot, compute, persist unlock growth."""
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    overall = await get_official_overall_cefr(db, student_id=student_id, language_id=language_id)
    anchor = _level_to_band(overall.level)

    if not grammar_engine_enabled():
        return disabled_snapshot(anchor_cefr=anchor)

    row = await lock_grammar_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        state = GrammarProgressionStudentState(
            student_id=student_id,
            language_id=language_id,
            stretch_allowed=bool(stretch_allowed) if stretch_allowed is not None else False,
        )
        return compute_from_state(anchor_cefr=anchor, student=state)

    payload = dict(row.promotion_readiness_json or {})
    bucket = progression_bucket_from_payload(payload)
    state = student_state_from_bucket(bucket, student_id=student_id, language_id=language_id)
    if stretch_allowed is not None:
        state = GrammarProgressionStudentState(
            student_id=state.student_id,
            language_id=state.language_id,
            completed_ids=state.completed_ids,
            unlocked_ids=state.unlocked_ids,
            current_grammar_id=state.current_grammar_id,
            stretch_allowed=bool(stretch_allowed),
        )

    snapshot = compute_from_state(anchor_cefr=anchor, student=state)
    persisted = apply_snapshot_unlocks_to_state(
        state,
        unlocked_ids=snapshot.unlocked_ids,
        current_grammar_id=snapshot.current_grammar_id,
    )
    new_bucket = bucket_from_student_state(persisted)
    row.promotion_readiness_json = merge_progression_into_payload(payload, new_bucket)
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return snapshot


async def record_grammar_topic_completed(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    grammar_id: str,
) -> GrammarProgressionSnapshot:
    """Mark a topic completed for unlock purposes and recompute unlocks.

    This is a progression-lifecycle write (not mastery scoring). Mastery may call
    this when a topic reaches mastered / completion threshold.
    """
    if not grammar_engine_enabled():
        overall = await get_official_overall_cefr(db, student_id=student_id, language_id=language_id)
        return disabled_snapshot(anchor_cefr=_level_to_band(overall.level))

    gid = normalize_to_grammar_id(grammar_id)
    if not gid:
        raise GrammarProgressionError(f"Cannot resolve grammar_id: {grammar_id}")

    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    row = await lock_grammar_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise GrammarProgressionError("LanguageProgression row unavailable")

    overall = await get_official_overall_cefr(db, student_id=student_id, language_id=language_id)
    anchor = _level_to_band(overall.level)
    payload = dict(row.promotion_readiness_json or {})
    state = student_state_from_bucket(
        progression_bucket_from_payload(payload),
        student_id=student_id,
        language_id=language_id,
    )
    pre = compute_from_state(anchor_cefr=anchor, student=state)
    if gid not in pre.unlocked_ids and gid not in state.unlocked_ids:
        raise GrammarProgressionError(f"Cannot complete locked topic: {gid}")

    state = GrammarProgressionStudentState(
        student_id=state.student_id,
        language_id=state.language_id,
        completed_ids=frozenset(state.completed_ids) | frozenset({gid}),
        unlocked_ids=state.unlocked_ids,
        current_grammar_id=state.current_grammar_id,
        stretch_allowed=state.stretch_allowed,
    )
    snapshot = compute_from_state(anchor_cefr=anchor, student=state)
    persisted = apply_snapshot_unlocks_to_state(
        state,
        unlocked_ids=snapshot.unlocked_ids,
        current_grammar_id=snapshot.current_grammar_id,
    )
    row.promotion_readiness_json = merge_progression_into_payload(
        payload, bucket_from_student_state(persisted)
    )
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return snapshot


# Backward-compatible alias during migration from cleared_ids naming.
record_grammar_topic_cleared = record_grammar_topic_completed


async def load_grammar_progression_snapshot_readonly(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
) -> GrammarProgressionSnapshot:
    """Read-only progression compute — no row locks, no unlock persistence (Wave D P1-3)."""
    overall = await get_official_overall_cefr(db, student_id=student_id, language_id=language_id)
    anchor = _level_to_band(overall.level)
    if not grammar_engine_enabled():
        return disabled_snapshot(anchor_cefr=anchor)

    from sqlalchemy import select

    from app.models.language.progression import LanguageProgression

    result = await db.execute(
        select(LanguageProgression).where(
            LanguageProgression.student_id == student_id,
            LanguageProgression.language_id == language_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        state = GrammarProgressionStudentState(student_id=student_id, language_id=language_id)
        return compute_from_state(anchor_cefr=anchor, student=state)

    payload = dict(row.promotion_readiness_json or {})
    state = student_state_from_bucket(
        progression_bucket_from_payload(payload),
        student_id=student_id,
        language_id=language_id,
    )
    return compute_from_state(anchor_cefr=anchor, student=state)


async def get_grammar_progression_snapshot(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    for_selection: bool = False,
) -> GrammarProgressionSnapshot:
    """Read-only progression snapshot for resolve/UI (Wave D — no writes).

    Unlock persistence remains on evaluate_and_persist_grammar_progression /
    record_grammar_topic_completed write paths only.
    """
    snapshot = await load_grammar_progression_snapshot_readonly(
        db, student_id=student_id, language_id=language_id
    )
    if for_selection:
        return selection_snapshot_or_disabled(snapshot)
    return snapshot
