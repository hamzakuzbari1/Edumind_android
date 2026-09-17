"""Grammar Runtime service (G3.2) — persistence + flag wiring."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.services.language_grammar_lesson_planner.types import GrammarLessonBlueprint
from app.services.language_grammar_lesson_runtime.dispatcher import GrammarRuntimeError
from app.services.language_grammar_lesson_runtime.flags import grammar_engine_enabled
from app.services.language_grammar_lesson_runtime.locking import lock_grammar_runtime_row
from app.services.language_grammar_lesson_runtime.orchestrator import (
    cancel,
    complete_current_step,
    create_session,
    pause,
    prepare,
    resume,
    run_to_completion,
    start,
    to_view,
)
from app.services.language_grammar_lesson_runtime.storage import (
    blueprint_from_runtime_bucket,
    bucket_from_session,
    merge_runtime_into_payload,
    runtime_bucket_from_payload,
    session_from_bucket,
)
from app.services.language_grammar_lesson_runtime.types import (
    GrammarRuntimeSession,
    GrammarRuntimeState,
    GrammarRuntimeView,
)
from app.services.language_progression_service import ensure_progression_row


def execute_blueprint(
    *,
    student_id: int,
    language_id: int,
    blueprint: GrammarLessonBlueprint,
    at: str | None = None,
) -> GrammarRuntimeView:
    """Pure path: run frozen blueprint to completion (or disabled empty view)."""
    if not grammar_engine_enabled():
        session = create_session(
            student_id=student_id,
            language_id=language_id,
            blueprint=blueprint,
            at=at or "1970-01-01T00:00:00Z",
        )
        # Mark disabled without executing
        disabled = GrammarRuntimeSession(
            student_id=session.student_id,
            language_id=session.language_id,
            grammar_id=session.grammar_id,
            lesson_id=session.lesson_id,
            state=GrammarRuntimeState.cancelled,
            cursor=session.cursor,
            blueprint_fingerprint=session.blueprint_fingerprint,
            completed_step_ids=(),
            pending_step_ids=session.pending_step_ids,
            events=session.events,
            evidence_requests=(),
            enabled=False,
        )
        return to_view(disabled)
    session = run_to_completion(
        student_id=student_id,
        language_id=language_id,
        blueprint=blueprint,
        at=at,
    )
    return to_view(session)


async def persist_session(
    db: AsyncSession,
    *,
    session: GrammarRuntimeSession,
    blueprint: GrammarLessonBlueprint | None = None,
) -> GrammarRuntimeSession:
    if not grammar_engine_enabled():
        raise GrammarRuntimeError("Grammar engine disabled")
    await ensure_progression_row(
        db, student_id=session.student_id, language_id=session.language_id
    )
    row = await lock_grammar_runtime_row(
        db, student_id=session.student_id, language_id=session.language_id
    )
    if row is None:
        raise GrammarRuntimeError("Progression row unavailable for runtime persistence")
    payload = dict(row.promotion_readiness_json or {})
    row.promotion_readiness_json = merge_runtime_into_payload(
        payload, bucket_from_session(session, blueprint=blueprint)
    )
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return session


async def load_session(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
) -> tuple[GrammarRuntimeSession | None, GrammarLessonBlueprint | None]:
    if not grammar_engine_enabled():
        return None, None
    await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    row = await lock_grammar_runtime_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        return None, None
    bucket = runtime_bucket_from_payload(dict(row.promotion_readiness_json or {}))
    return session_from_bucket(bucket), blueprint_from_runtime_bucket(bucket)


# Re-export orchestrator ops for service consumers
__all__ = [
    "cancel",
    "complete_current_step",
    "create_session",
    "execute_blueprint",
    "load_session",
    "pause",
    "persist_session",
    "prepare",
    "resume",
    "run_to_completion",
    "start",
    "to_view",
]
