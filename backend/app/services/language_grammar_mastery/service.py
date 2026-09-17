"""Grammar Mastery service (G2.2) — evidence ingest, scoring, persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.progression import LanguageProgression
from app.services.language_grammar.enums import GrammarMasteryState
from app.services.language_grammar_catalog.catalog import get_default_catalog
from app.services.language_grammar_evidence.types import GrammarEvidenceBatch
from app.services.language_grammar_evidence.validation import (
    GrammarEvidenceError,
    validate_batch,
)
from app.services.language_grammar_mastery.engine import (
    GrammarMasteryError,
    apply_observations,
    disabled_mastery_snapshot,
    empty_snapshot,
)
from app.services.language_grammar_mastery.flags import (
    grammar_engine_enabled,
    grammar_engine_select_enabled,
)
from app.services.language_grammar_mastery.locking import lock_grammar_mastery_row
from app.services.language_grammar_mastery.storage import (
    bucket_from_snapshot,
    mastery_bucket_from_payload,
    merge_mastery_into_payload,
    snapshot_from_bucket,
)
from app.services.language_grammar_mastery.types import (
    GrammarMasterySnapshot,
    PublicGrammarMasteryView,
    to_public_view,
)
from app.services.language_progression_service import ensure_progression_row


async def _load_progression_row_readonly(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LanguageProgression | None:
    result = await db.execute(
        select(LanguageProgression).where(
            LanguageProgression.student_id == student_id,
            LanguageProgression.language_id == language_id,
        )
    )
    return result.scalar_one_or_none()


def compute_mastery_from_evidence(
    *,
    student_id: int,
    language_id: int,
    batch: GrammarEvidenceBatch,
    prior: GrammarMasterySnapshot | None = None,
) -> GrammarMasterySnapshot:
    """Pure path: validate evidence → apply → snapshot. Respects ENABLED flag.

    Mastery does not import Progression — proficiency is independent of unlock state.
    """
    if not grammar_engine_enabled():
        return disabled_mastery_snapshot(student_id=student_id, language_id=language_id)

    validated = validate_batch(batch)
    if not validated.valid:
        raise GrammarEvidenceError("; ".join(validated.issues))

    catalog = get_default_catalog()
    base = prior or empty_snapshot(student_id=student_id, language_id=language_id)
    if base.student_id != student_id or base.language_id != language_id:
        raise GrammarMasteryError("Prior snapshot student/language mismatch")
    return apply_observations(base, validated.observations, catalog=catalog)


def public_views(
    snapshot: GrammarMasterySnapshot,
    *,
    for_selection: bool = False,
) -> tuple[PublicGrammarMasteryView, ...]:
    """Public overall-only projection. SELECT gate can hide when requested."""
    if not snapshot.enabled:
        return ()
    if for_selection and not grammar_engine_select_enabled():
        return ()
    return tuple(to_public_view(r) for r in snapshot.records)


def completion_ready_ids(snapshot: GrammarMasterySnapshot) -> tuple[str, ...]:
    """Topics at mastered state — Progression may sync into completed_ids."""
    return tuple(
        sorted(r.grammar_id for r in snapshot.records if r.state is GrammarMasteryState.mastered)
    )


async def apply_evidence_and_persist(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    batch: GrammarEvidenceBatch,
) -> GrammarMasterySnapshot:
    """Validate evidence, update mastery, persist under grammar.mastery JSONB."""
    if not grammar_engine_enabled():
        return disabled_mastery_snapshot(student_id=student_id, language_id=language_id)

    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    row = await lock_grammar_mastery_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        # Ephemeral compute when progression row unavailable
        return compute_mastery_from_evidence(
            student_id=student_id,
            language_id=language_id,
            batch=batch,
        )

    payload = dict(row.promotion_readiness_json or {})
    prior = snapshot_from_bucket(
        mastery_bucket_from_payload(payload),
        student_id=student_id,
        language_id=language_id,
    )
    snapshot = compute_mastery_from_evidence(
        student_id=student_id,
        language_id=language_id,
        batch=batch,
        prior=prior,
    )
    bucket = bucket_from_snapshot(snapshot)
    # Wave D P1-5: pin curriculum_version on mastery cache (migration support later).
    try:
        bucket["curriculum_version"] = str(get_default_catalog().version or "1.1.0")
    except Exception:  # noqa: BLE001
        bucket["curriculum_version"] = "1.1.0"
    row.promotion_readiness_json = merge_mastery_into_payload(payload, bucket)
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return snapshot


async def get_grammar_mastery_snapshot(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
) -> GrammarMasterySnapshot:
    """Read-only mastery snapshot — never locks or persists (Wave D P1-3)."""
    if not grammar_engine_enabled():
        return disabled_mastery_snapshot(student_id=student_id, language_id=language_id)
    row = await _load_progression_row_readonly(
        db, student_id=student_id, language_id=language_id
    )
    if row is None:
        return empty_snapshot(student_id=student_id, language_id=language_id)
    return snapshot_from_bucket(
        mastery_bucket_from_payload(dict(row.promotion_readiness_json or {})),
        student_id=student_id,
        language_id=language_id,
    )


# Backward-compatible alias — resolve/read paths must use the readonly getter.
get_grammar_mastery_snapshot_readonly = get_grammar_mastery_snapshot
