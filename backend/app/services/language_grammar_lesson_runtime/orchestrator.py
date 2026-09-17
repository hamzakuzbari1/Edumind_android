"""Grammar Runtime Orchestrator (G3.2/V1.1) — executes frozen blueprints only."""

from __future__ import annotations

from dataclasses import replace

from app.services.language_grammar_lesson_planner.types import GrammarLessonBlueprint
from app.services.language_grammar_lesson_runtime.dispatcher import (
    GrammarRuntimeError,
    dispatch_step,
)
from app.services.language_grammar_lesson_runtime.events import make_event, utc_now_iso
from app.services.language_grammar_lesson_runtime.executors.registry import (
    GrammarExecutorRegistry,
    get_default_registry,
)
from app.services.language_grammar_lesson_runtime.types import (
    ALLOWED_TRANSITIONS,
    GrammarRuntimeCursor,
    GrammarRuntimeEvent,
    GrammarRuntimeEventType,
    GrammarRuntimeSession,
    GrammarRuntimeState,
    GrammarRuntimeView,
    GrammarStepExecutionRecord,
)
from app.services.language_grammar_skill_executor import ExecutionIdGuard


def _assert_transition(current: GrammarRuntimeState, target: GrammarRuntimeState) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise GrammarRuntimeError(f"Illegal transition {current.value} -> {target.value}")


def _next_seq(session: GrammarRuntimeSession) -> int:
    if not session.events:
        return 1
    return max(e.sequence for e in session.events) + 1


def _append_event(
    session: GrammarRuntimeSession,
    event_type: GrammarRuntimeEventType,
    *,
    at: str,
    step_id: str | None = None,
    step_kind=None,
    detail: str = "",
) -> tuple[GrammarRuntimeEvent, ...]:
    event = make_event(
        sequence=_next_seq(session),
        event_type=event_type,
        lesson_id=session.lesson_id,
        at=at,
        step_id=step_id,
        step_kind=step_kind,
        detail=detail,
    )
    return session.events + (event,)


def _pending_ids(blueprint: GrammarLessonBlueprint, completed: tuple[str, ...]) -> tuple[str, ...]:
    done = set(completed)
    return tuple(s.step_id for s in blueprint.steps if s.step_id not in done)


def _cursor_for(
    blueprint: GrammarLessonBlueprint,
    *,
    step_index: int,
) -> GrammarRuntimeCursor:
    if step_index < 0 or step_index >= len(blueprint.steps):
        return GrammarRuntimeCursor(
            blueprint_fingerprint=blueprint.fingerprint,
            step_index=step_index,
            current_step_id=None,
            current_step_kind=None,
            current_reinforcement_skill=None,
        )
    step = blueprint.steps[step_index]
    return GrammarRuntimeCursor(
        blueprint_fingerprint=blueprint.fingerprint,
        step_index=step_index,
        current_step_id=step.step_id,
        current_step_kind=step.kind,
        current_reinforcement_skill=step.skill,
    )


def _validate_blueprint(blueprint: GrammarLessonBlueprint) -> None:
    if not blueprint.frozen:
        raise GrammarRuntimeError("Blueprint must be frozen")
    if not blueprint.enabled:
        raise GrammarRuntimeError("Blueprint is disabled")
    if not blueprint.steps:
        raise GrammarRuntimeError("Blueprint has no steps")
    if not blueprint.fingerprint:
        raise GrammarRuntimeError("Blueprint missing fingerprint")
    ids = [s.step_id for s in blueprint.steps]
    if len(ids) != len(set(ids)):
        raise GrammarRuntimeError("Blueprint has duplicate step_ids")


def _record_from_dispatch(result, *, step_id: str) -> GrammarStepExecutionRecord | None:
    if result.execution_result is None:
        return None
    exe = result.execution_result
    return GrammarStepExecutionRecord(
        execution_id=exe.execution_id,
        skill_executor_id=exe.executor_metadata.executor_id,
        activity_id=result.activity_id or "",
        step_id=step_id,
        status=exe.status.value,
        lifecycle_phases=tuple(exe.executor_metadata.lifecycle_phases_completed),
        duration_ms=exe.timing.duration_ms,
        started_at=exe.timing.started_at,
        finished_at=exe.timing.finished_at,
        evidence_observation_ids=tuple(o.observation_id for o in exe.generated_evidence),
        notes=exe.notes,
    )


def to_view(session: GrammarRuntimeSession) -> GrammarRuntimeView:
    return GrammarRuntimeView(
        session=session,
        current_state=session.state,
        completed_steps=session.completed_step_ids,
        pending_steps=session.pending_step_ids,
        events=session.events,
        expected_evidence_requests=session.evidence_requests,
    )


def create_session(
    *,
    student_id: int,
    language_id: int,
    blueprint: GrammarLessonBlueprint,
    at: str | None = None,
) -> GrammarRuntimeSession:
    """CREATED — bind a frozen blueprint; no step execution yet."""
    _validate_blueprint(blueprint)
    ts = at or utc_now_iso()
    lesson_id = blueprint.lesson_id or f"runtime_{blueprint.grammar_id}_{student_id}"
    pending = tuple(s.step_id for s in blueprint.steps)
    session = GrammarRuntimeSession(
        student_id=student_id,
        language_id=language_id,
        grammar_id=blueprint.grammar_id,
        lesson_id=lesson_id,
        state=GrammarRuntimeState.created,
        cursor=_cursor_for(blueprint, step_index=0),
        blueprint_fingerprint=blueprint.fingerprint,
        completed_step_ids=(),
        pending_step_ids=pending,
        events=(),
        evidence_requests=(),
        step_executions=(),
        package_id="",
        enabled=True,
    )
    events = _append_event(
        session,
        GrammarRuntimeEventType.lesson_created,
        at=ts,
        detail=f"fingerprint:{blueprint.fingerprint}",
    )
    return replace(session, events=events)


def prepare(
    session: GrammarRuntimeSession,
    blueprint: GrammarLessonBlueprint,
    *,
    at: str | None = None,
) -> GrammarRuntimeSession:
    """CREATED -> READY after blueprint fingerprint check."""
    _assert_transition(session.state, GrammarRuntimeState.ready)
    _validate_blueprint(blueprint)
    if blueprint.fingerprint != session.blueprint_fingerprint:
        raise GrammarRuntimeError("Blueprint fingerprint mismatch")
    ts = at or utc_now_iso()
    events = _append_event(session, GrammarRuntimeEventType.lesson_ready, at=ts)
    return replace(
        session,
        state=GrammarRuntimeState.ready,
        cursor=_cursor_for(blueprint, step_index=0),
        pending_step_ids=_pending_ids(blueprint, session.completed_step_ids),
        events=events,
    )


def start(
    session: GrammarRuntimeSession,
    blueprint: GrammarLessonBlueprint,
    *,
    at: str | None = None,
) -> GrammarRuntimeSession:
    """READY -> RUNNING and emit LessonStarted + StepStarted for first step."""
    _assert_transition(session.state, GrammarRuntimeState.running)
    _validate_blueprint(blueprint)
    if blueprint.fingerprint != session.blueprint_fingerprint:
        raise GrammarRuntimeError("Blueprint fingerprint mismatch")
    if not blueprint.steps:
        raise GrammarRuntimeError("No steps to start")
    ts = at or utc_now_iso()
    step = blueprint.steps[0]
    events = _append_event(session, GrammarRuntimeEventType.lesson_started, at=ts)
    mid = replace(
        session,
        state=GrammarRuntimeState.running,
        cursor=_cursor_for(blueprint, step_index=0),
        pending_step_ids=_pending_ids(blueprint, session.completed_step_ids),
        events=events,
    )
    events2 = _append_event(
        mid,
        GrammarRuntimeEventType.step_started,
        at=ts,
        step_id=step.step_id,
        step_kind=step.kind,
    )
    return replace(mid, events=events2)


def complete_current_step(
    session: GrammarRuntimeSession,
    blueprint: GrammarLessonBlueprint,
    *,
    registry: GrammarExecutorRegistry | None = None,
    at: str | None = None,
    execution_guard: ExecutionIdGuard | None = None,
) -> GrammarRuntimeSession:
    """RUNNING -> STEP_COMPLETED (or COMPLETED if last step). Dispatches via Skill Registry."""
    if session.state is not GrammarRuntimeState.running:
        raise GrammarRuntimeError(f"complete_current_step requires running, got {session.state}")
    _validate_blueprint(blueprint)
    if blueprint.fingerprint != session.blueprint_fingerprint:
        raise GrammarRuntimeError("Blueprint fingerprint mismatch")

    idx = session.cursor.step_index
    if idx < 0 or idx >= len(blueprint.steps):
        raise GrammarRuntimeError("Cursor out of range")
    step = blueprint.steps[idx]
    ts = at or utc_now_iso()
    guard = execution_guard or ExecutionIdGuard()

    try:
        result = dispatch_step(
            step,
            blueprint,
            registry=registry or get_default_registry(),
            student_id=session.student_id,
            language_id=session.language_id,
            lesson_id=session.lesson_id,
            step_index=idx,
            completed_step_ids=session.completed_step_ids,
            as_of=ts,
            execution_guard=guard,
        )
    except GrammarRuntimeError as exc:
        return fail(session, reason=str(exc), at=ts)

    if not result.success:
        return fail(session, reason=result.notes or "step dispatch failed", at=ts)

    _assert_transition(session.state, GrammarRuntimeState.step_completed)
    completed = session.completed_step_ids + (step.step_id,)
    evidence = session.evidence_requests
    if result.evidence_request is not None:
        evidence = evidence + (result.evidence_request,)

    record = _record_from_dispatch(result, step_id=step.step_id)
    step_executions = session.step_executions + ((record,) if record is not None else ())

    events = _append_event(
        session,
        GrammarRuntimeEventType.step_completed,
        at=ts,
        step_id=step.step_id,
        step_kind=step.kind,
        detail=result.notes,
    )
    pending = _pending_ids(blueprint, completed)

    mid = replace(
        session,
        state=GrammarRuntimeState.step_completed,
        completed_step_ids=completed,
        pending_step_ids=pending,
        events=events,
        evidence_requests=evidence,
        step_executions=step_executions,
    )

    if not pending:
        return _finish_completed(mid, at=ts)

    next_index = idx + 1
    next_step = blueprint.steps[next_index]
    _assert_transition(GrammarRuntimeState.step_completed, GrammarRuntimeState.running)
    events2 = _append_event(
        mid,
        GrammarRuntimeEventType.step_started,
        at=ts,
        step_id=next_step.step_id,
        step_kind=next_step.kind,
    )
    return replace(
        mid,
        state=GrammarRuntimeState.running,
        cursor=_cursor_for(blueprint, step_index=next_index),
        events=events2,
    )


def _finish_completed(session: GrammarRuntimeSession, *, at: str) -> GrammarRuntimeSession:
    _assert_transition(session.state, GrammarRuntimeState.completed)
    events = _append_event(session, GrammarRuntimeEventType.lesson_completed, at=at)
    return replace(
        session,
        state=GrammarRuntimeState.completed,
        cursor=GrammarRuntimeCursor(
            blueprint_fingerprint=session.blueprint_fingerprint,
            step_index=session.cursor.step_index,
            current_step_id=None,
            current_step_kind=None,
        ),
        pending_step_ids=(),
        events=events,
    )


def pause(session: GrammarRuntimeSession, *, at: str | None = None) -> GrammarRuntimeSession:
    _assert_transition(session.state, GrammarRuntimeState.paused)
    ts = at or utc_now_iso()
    events = _append_event(session, GrammarRuntimeEventType.lesson_paused, at=ts)
    return replace(session, state=GrammarRuntimeState.paused, events=events)


def resume(
    session: GrammarRuntimeSession,
    blueprint: GrammarLessonBlueprint,
    *,
    at: str | None = None,
) -> GrammarRuntimeSession:
    _assert_transition(session.state, GrammarRuntimeState.running)
    if blueprint.fingerprint != session.blueprint_fingerprint:
        raise GrammarRuntimeError("Blueprint fingerprint mismatch")
    ts = at or utc_now_iso()
    events = _append_event(session, GrammarRuntimeEventType.lesson_resumed, at=ts)
    return replace(session, state=GrammarRuntimeState.running, events=events)


def cancel(session: GrammarRuntimeSession, *, at: str | None = None) -> GrammarRuntimeSession:
    _assert_transition(session.state, GrammarRuntimeState.cancelled)
    ts = at or utc_now_iso()
    events = _append_event(session, GrammarRuntimeEventType.lesson_cancelled, at=ts)
    return replace(
        session,
        state=GrammarRuntimeState.cancelled,
        events=events,
        failure_reason=None,
    )


def fail(
    session: GrammarRuntimeSession,
    *,
    reason: str,
    at: str | None = None,
) -> GrammarRuntimeSession:
    if session.state in (
        GrammarRuntimeState.completed,
        GrammarRuntimeState.failed,
        GrammarRuntimeState.cancelled,
    ):
        raise GrammarRuntimeError(f"Cannot fail from terminal state {session.state}")
    if GrammarRuntimeState.failed not in ALLOWED_TRANSITIONS.get(session.state, frozenset()):
        raise GrammarRuntimeError(f"Illegal transition {session.state.value} -> failed")
    ts = at or utc_now_iso()
    events = _append_event(
        session,
        GrammarRuntimeEventType.lesson_failed,
        at=ts,
        detail=reason,
    )
    return replace(
        session,
        state=GrammarRuntimeState.failed,
        events=events,
        failure_reason=reason,
    )


def run_to_completion(
    *,
    student_id: int,
    language_id: int,
    blueprint: GrammarLessonBlueprint,
    registry: GrammarExecutorRegistry | None = None,
    at: str | None = None,
) -> GrammarRuntimeSession:
    """Deterministic full execution helper for tests / replay."""
    ts = at or "2026-01-01T00:00:00Z"
    session = create_session(
        student_id=student_id, language_id=language_id, blueprint=blueprint, at=ts
    )
    session = prepare(session, blueprint, at=ts)
    session = start(session, blueprint, at=ts)
    execution_guard = ExecutionIdGuard()
    step_guard = 0
    while session.state is GrammarRuntimeState.running:
        session = complete_current_step(
            session,
            blueprint,
            registry=registry,
            at=ts,
            execution_guard=execution_guard,
        )
        step_guard += 1
        if step_guard > len(blueprint.steps) + 2:
            raise GrammarRuntimeError("run_to_completion exceeded step guard")
    return session
