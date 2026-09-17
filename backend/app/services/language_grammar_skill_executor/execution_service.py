"""Skill Execution Engine / Execution Service (V1.5).

Owns interaction lifecycle only. Never Grammar/Progression/Mastery/Review/Authoring.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from app.services.language_grammar_activity_spec import ActivitySpecification
from app.services.language_grammar_evidence.types import GrammarEvidenceObservation
from app.services.language_grammar_skill_executor.engine_validation import (
    validate_executor_available,
    validate_grammar_targets,
    validate_session_transition,
    validate_specification,
)
from app.services.language_grammar_skill_executor.errors import (
    SkillExecutorDisabledError,
    SkillExecutorError,
)
from app.services.language_grammar_skill_executor.evidence_adapter import (
    adapt_execution_to_evidence,
    source_skill_for_executor,
)
from app.services.language_grammar_skill_executor.flags import (
    skill_execution_engine_enabled,
    skill_executor_enabled,
)
from app.services.language_grammar_skill_executor.registry import (
    SkillExecutorRegistry,
    get_default_skill_executor_registry,
)
from app.services.language_grammar_skill_executor.resolution import resolve_executor
from app.services.language_grammar_skill_executor.session import (
    ExecutionEngineState,
    ExecutionLifecycleEvent,
    ExecutionLifecycleEventType,
    ExecutionSession,
    SessionStatus,
    TERMINAL_SESSION_STATUSES,
)
from app.services.language_grammar_skill_executor.storage import (
    ExecutionSessionStore,
    get_default_execution_session_store,
)
from app.services.language_grammar_skill_executor.types import (
    CompletionState,
    ExecutionContext,
    ExecutionFeatureFlags,
    ExecutionMetadata,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTiming,
    ExecutorMetadata,
    StudentContext,
    TeacherPersona,
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _emit(
    state: ExecutionEngineState,
    event_type: ExecutionLifecycleEventType,
    *,
    at: str,
    detail: str = "",
    from_status: str = "",
    to_status: str = "",
) -> None:
    seq = (state.events[-1].sequence + 1) if state.events else 1
    state.events.append(
        ExecutionLifecycleEvent(
            sequence=seq,
            event_type=event_type,
            execution_session_id=state.session.execution_session_id,
            at=at,
            detail=detail,
            from_status=from_status,
            to_status=to_status,
        )
    )


def _transition(
    state: ExecutionEngineState,
    target: SessionStatus,
    *,
    at: str,
    event_type: ExecutionLifecycleEventType | None = None,
    detail: str = "",
    **session_updates: object,
) -> ExecutionEngineState:
    current = state.session.status
    validate_session_transition(state.session, target)
    from_status = current.value
    state.session = replace(state.session, status=target, **session_updates)  # type: ignore[arg-type]
    state.status_history.append(target.value)
    state.snapshot_version += 1
    if event_type is not None:
        _emit(
            state,
            event_type,
            at=at,
            detail=detail,
            from_status=from_status,
            to_status=target.value,
        )
    return state


def _require_engine_enabled(context: ExecutionContext, *, require_enabled: bool) -> None:
    if not require_enabled:
        return
    # Context flags mirror Runtime bridge — allow explicit enable without Settings.
    if context.feature_flags.grammar_engine_enabled and context.feature_flags.skill_executor_enabled:
        return
    if skill_execution_engine_enabled() or skill_executor_enabled():
        return
    raise SkillExecutorDisabledError(
        "Skill execution engine disabled "
        "(LANG_GRAMMAR_SKILL_EXECUTION_ENGINE_ENABLED / SKILL_EXECUTOR)"
    )


def build_execution_context(
    specification: ActivitySpecification,
    *,
    student: StudentContext,
    teacher_persona: TeacherPersona | None = None,
    runtime_session_id: str = "",
    blueprint_id: str = "",
    execution_id: str = "",
    localization: str = "",
    as_of: str = "",
    attempt_index: int = 0,
    preferred_executor_id: str = "",
    feature_flags: ExecutionFeatureFlags | None = None,
) -> ExecutionContext:
    """Build ExecutionContext — no Grammar decision logic."""
    locale = localization or student.locale or "en"
    return ExecutionContext(
        specification=specification,
        student=student,
        teacher_persona=teacher_persona or TeacherPersona(),
        runtime_session_id=runtime_session_id or f"rt_{student.student_id}",
        blueprint_id=blueprint_id or specification.lesson_id or "blueprint",
        execution_id=execution_id or _new_id("exec"),
        localization=locale,
        feature_flags=feature_flags
        or ExecutionFeatureFlags(
            grammar_engine_enabled=True,
            skill_executor_enabled=True,
            skill_executor_strict=True,
        ),
        metadata=ExecutionMetadata(
            as_of=as_of,
            attempt_index=attempt_index,
            preferred_executor_id=preferred_executor_id,
        ),
    )


def create_execution(
    specification: ActivitySpecification,
    *,
    student: StudentContext,
    teacher_persona: TeacherPersona | None = None,
    localization: str = "",
    as_of: str = "",
    preferred_executor_id: str = "",
    registry: SkillExecutorRegistry | None = None,
    store: ExecutionSessionStore | None = None,
    require_enabled: bool = False,
    execution_session_id: str = "",
    execution_attempt_id: str = "",
) -> ExecutionEngineState:
    """Create an execution session in Created state."""
    validate_specification(specification)
    targets = tuple(specification.grammar_targets) or (
        (specification.grammar_topic,) if specification.grammar_topic else ()
    )
    validate_grammar_targets(targets)

    reg = registry or get_default_skill_executor_registry()
    teacher = teacher_persona or TeacherPersona()
    context = build_execution_context(
        specification,
        student=student,
        teacher_persona=teacher,
        localization=localization,
        as_of=as_of,
        preferred_executor_id=preferred_executor_id,
    )
    _require_engine_enabled(context, require_enabled=require_enabled)
    validate_executor_available(
        reg,
        activity_type=specification.activity_type,
        preferred_executor_id=preferred_executor_id,
    )

    session = ExecutionSession(
        execution_session_id=execution_session_id or _new_id("esess"),
        execution_attempt_id=execution_attempt_id or _new_id("eatt"),
        activity_id=specification.activity_id,
        activity_type=specification.activity_type,
        student_id=student.student_id,
        teacher_id=teacher.teacher_id,
        grammar_targets=targets,
        status=SessionStatus.created,
        localization=context.localization,
    )
    state = ExecutionEngineState(
        session=session,
        context=context,
        specification=specification,
        status_history=[SessionStatus.created.value],
    )
    _emit(
        state,
        ExecutionLifecycleEventType.execution_created,
        at=as_of,
        detail=specification.activity_id,
        to_status=SessionStatus.created.value,
    )
    (store or get_default_execution_session_store()).save(state)
    return state


def start_execution(
    state: ExecutionEngineState,
    *,
    registry: SkillExecutorRegistry | None = None,
    store: ExecutionSessionStore | None = None,
    at: str = "",
) -> ExecutionEngineState:
    """Created → Initializing → Running → WaitingForStudent; emit ExecutionStarted."""
    reg = registry or get_default_skill_executor_registry()
    preferred = state.context.metadata.preferred_executor_id
    executor = resolve_executor(
        state.context,
        registry=reg,
        preferred_executor_id=preferred or None,
    )

    state = _transition(
        state,
        SessionStatus.initializing,
        at=at,
        detail="initialize",
    )
    executor.initialize(state.context)
    executor.prepare(state.context)
    executor.validate(state.context)

    state = _transition(
        state,
        SessionStatus.running,
        at=at,
        detail=f"executor={executor.executor_id}",
        executor_id=executor.executor_id,
        started_at=at or state.session.started_at or "started",
    )
    state = _transition(
        state,
        SessionStatus.waiting_for_student,
        at=at,
        event_type=ExecutionLifecycleEventType.execution_started,
        detail="awaiting_student_response",
    )
    # Keep context execution_id aligned with session attempt for evidence ids.
    state.context = replace(
        state.context,
        execution_id=state.session.execution_attempt_id or state.context.execution_id,
    )
    (store or get_default_execution_session_store()).save(state)
    return state


def submit_student_response(
    state: ExecutionEngineState,
    student_response: str,
    *,
    store: ExecutionSessionStore | None = None,
    at: str = "",
) -> ExecutionEngineState:
    """WaitingForStudent → Evaluating; emit StudentResponded."""
    state = _transition(
        state,
        SessionStatus.evaluating,
        at=at,
        event_type=ExecutionLifecycleEventType.student_responded,
        detail=(student_response or "")[:120],
        student_response=student_response or "",
    )
    (store or get_default_execution_session_store()).save(state)
    return state


def complete_evaluation(
    state: ExecutionEngineState,
    *,
    registry: SkillExecutorRegistry | None = None,
    store: ExecutionSessionStore | None = None,
    at: str = "",
    success: bool = True,
    completion_reason: str = "",
    metrics: dict[str, str] | None = None,
    emit_evidence: bool = True,
) -> ExecutionEngineState:
    """Evaluating → Completed|Failed; run executor execute/complete + evidence adapter."""
    if state.session.status is not SessionStatus.evaluating:
        raise SkillExecutorError(
            f"complete_evaluation requires evaluating status, got {state.session.status.value}"
        )

    reg = registry or get_default_skill_executor_registry()
    preferred = state.context.metadata.preferred_executor_id or state.session.executor_id
    executor = resolve_executor(
        state.context,
        registry=reg,
        preferred_executor_id=preferred or None,
    )

    if not success:
        result = ExecutionResult(
            execution_id=state.context.execution_id,
            status=ExecutionStatus.failed,
            completion_state=CompletionState.incomplete,
            completion_status="failed",
            completion_reason=completion_reason or "evaluation_failed",
            student_response=state.session.student_response,
            metrics=dict(metrics or {}),
            timing=ExecutionTiming(started_at=state.session.started_at, finished_at=at),
            executor_metadata=ExecutorMetadata(executor_id=executor.executor_id),
        )
        state.result = result
        _emit(
            state,
            ExecutionLifecycleEventType.evaluation_completed,
            at=at,
            detail="failed",
            from_status=state.session.status.value,
            to_status=SessionStatus.failed.value,
        )
        state = _transition(
            state,
            SessionStatus.failed,
            at=at,
            event_type=ExecutionLifecycleEventType.execution_failed,
            detail=completion_reason or "evaluation_failed",
            completed_at=at or "failed",
        )
        (store or get_default_execution_session_store()).save(state)
        return state

    result = executor.execute(state.context)
    # Apply student response onto collected outputs when present.
    if state.session.student_response and result.collected_outputs:
        updated_outputs = []
        for index, out in enumerate(result.collected_outputs):
            if index == 0:
                updated_outputs.append(
                    replace(out, value=state.session.student_response, present=True)
                )
            else:
                updated_outputs.append(out)
        result = replace(result, collected_outputs=tuple(updated_outputs))

    result = executor.complete(state.context, result)
    result = replace(
        result,
        status=ExecutionStatus.completed,
        completion_state=CompletionState.complete,
        completion_status="completed",
        completion_reason=completion_reason or "student_response_accepted",
        student_response=state.session.student_response,
        metrics={
            "output_count": str(len(result.collected_outputs)),
            "activity_type": state.session.activity_type,
            **dict(metrics or {}),
        },
        timing=ExecutionTiming(
            started_at=state.session.started_at or result.timing.started_at,
            finished_at=at or result.timing.finished_at or "finished",
            duration_ms=result.timing.duration_ms,
        ),
        executor_metadata=replace(
            result.executor_metadata,
            executor_id=executor.executor_id or state.session.executor_id,
        ),
    )

    observations: tuple[GrammarEvidenceObservation, ...] = ()
    if emit_evidence:
        observations = adapt_execution_to_evidence(
            result,
            context=state.context,
            source_skill=source_skill_for_executor(executor.executor_id),
        )
        result = replace(result, generated_evidence=observations)

    try:
        executor.cleanup(state.context)
    except Exception:  # noqa: BLE001 — cleanup must not block terminal transition
        pass

    state.result = result
    state.observations = observations
    _emit(
        state,
        ExecutionLifecycleEventType.evaluation_completed,
        at=at,
        detail=f"observations={len(observations)}",
        from_status=state.session.status.value,
        to_status=SessionStatus.completed.value,
    )
    state = _transition(
        state,
        SessionStatus.completed,
        at=at,
        event_type=ExecutionLifecycleEventType.execution_completed,
        detail=result.completion_reason,
        completed_at=at or "completed",
        executor_id=executor.executor_id or state.session.executor_id,
    )
    (store or get_default_execution_session_store()).save(state)
    return state


def cancel_execution(
    state: ExecutionEngineState,
    *,
    reason: str = "",
    store: ExecutionSessionStore | None = None,
    at: str = "",
) -> ExecutionEngineState:
    if state.session.status in TERMINAL_SESSION_STATUSES:
        return state
    state = _transition(
        state,
        SessionStatus.cancelled,
        at=at,
        event_type=ExecutionLifecycleEventType.execution_cancelled,
        detail=reason or "cancelled",
        completed_at=at or "cancelled",
    )
    state.result = ExecutionResult(
        execution_id=state.context.execution_id,
        status=ExecutionStatus.cancelled,
        completion_state=CompletionState.incomplete,
        completion_status="cancelled",
        completion_reason=reason or "cancelled",
        student_response=state.session.student_response,
        timing=ExecutionTiming(started_at=state.session.started_at, finished_at=at),
        executor_metadata=ExecutorMetadata(executor_id=state.session.executor_id),
    )
    (store or get_default_execution_session_store()).save(state)
    return state


def fail_execution(
    state: ExecutionEngineState,
    *,
    reason: str = "",
    store: ExecutionSessionStore | None = None,
    at: str = "",
) -> ExecutionEngineState:
    if state.session.status in TERMINAL_SESSION_STATUSES:
        return state
    state = _transition(
        state,
        SessionStatus.failed,
        at=at,
        event_type=ExecutionLifecycleEventType.execution_failed,
        detail=reason or "failed",
        completed_at=at or "failed",
    )
    state.result = ExecutionResult(
        execution_id=state.context.execution_id,
        status=ExecutionStatus.failed,
        completion_state=CompletionState.incomplete,
        completion_status="failed",
        completion_reason=reason or "failed",
        student_response=state.session.student_response,
        timing=ExecutionTiming(started_at=state.session.started_at, finished_at=at),
        executor_metadata=ExecutorMetadata(executor_id=state.session.executor_id),
    )
    (store or get_default_execution_session_store()).save(state)
    return state


def run_execution(
    specification: ActivitySpecification,
    *,
    student: StudentContext,
    student_response: str = "",
    teacher_persona: TeacherPersona | None = None,
    localization: str = "",
    as_of: str = "",
    preferred_executor_id: str = "",
    registry: SkillExecutorRegistry | None = None,
    store: ExecutionSessionStore | None = None,
    require_enabled: bool = False,
    emit_evidence: bool = True,
) -> ExecutionEngineState:
    """Happy-path orchestration: create → start → respond → complete."""
    state = create_execution(
        specification,
        student=student,
        teacher_persona=teacher_persona,
        localization=localization,
        as_of=as_of,
        preferred_executor_id=preferred_executor_id,
        registry=registry,
        store=store,
        require_enabled=require_enabled,
    )
    state = start_execution(state, registry=registry, store=store, at=as_of or "t1")
    state = submit_student_response(
        state,
        student_response,
        store=store,
        at=as_of or "t2",
    )
    return complete_evaluation(
        state,
        registry=registry,
        store=store,
        at=as_of or "t3",
        emit_evidence=emit_evidence,
    )


def replay_execution(
    execution_session_id: str,
    *,
    store: ExecutionSessionStore | None = None,
) -> ExecutionEngineState:
    """Replay a stored execution session from persisted state (no re-authoring)."""
    state = (store or get_default_execution_session_store()).get(execution_session_id)
    # Re-derive observations from stored result when present (deterministic).
    if state.result is not None and state.result.status is ExecutionStatus.completed:
        if not state.observations and state.result.generated_evidence:
            state.observations = tuple(state.result.generated_evidence)
        elif not state.observations:
            state.observations = adapt_execution_to_evidence(
                state.result,
                context=state.context,
                source_skill=source_skill_for_executor(state.session.executor_id),
            )
    return state


def collect_evidence(state: ExecutionEngineState) -> tuple[GrammarEvidenceObservation, ...]:
    """Return observations only — never mastery scores."""
    if state.observations:
        return tuple(state.observations)
    if state.result is None:
        return ()
    return tuple(state.result.generated_evidence)
