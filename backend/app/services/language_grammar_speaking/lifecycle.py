"""Speaking Domain lifecycle (V1.2A) — deterministic, no LLM/audio."""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from app.services.language_grammar_speaking.enums import (
    SpeakingAttemptStatus,
    SpeakingCompletionState,
    SpeakingEventType,
    SpeakingLifecyclePhase,
    SpeakingSessionStatus,
    SpeakingSpeaker,
    SpeakingTurnStatus,
)
from app.services.language_grammar_speaking.errors import SpeakingLifecycleError, SpeakingStateError
from app.services.language_grammar_speaking.evidence import (
    build_speaking_evidence,
    map_speaking_evidence_to_observations,
)
from app.services.language_grammar_speaking.state_machine import (
    assert_attempt_transition,
    assert_session_transition,
    assert_turn_transition,
)
from app.services.language_grammar_speaking.types import (
    SpeakingAttempt,
    SpeakingContext,
    SpeakingEvent,
    SpeakingResult,
    SpeakingSession,
    SpeakingSessionView,
    SpeakingState,
    SpeakingTiming,
    SpeakingTurn,
)
from app.services.language_grammar_speaking.validation import (
    validate_context,
    validate_grammar_targets,
    validate_session_state,
)


def _now(at: str | None) -> str:
    return at or ""


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _emit(
    state: SpeakingState,
    event_type: SpeakingEventType,
    *,
    at: str,
    attempt_id: str | None = None,
    turn_id: str | None = None,
    detail: str = "",
) -> None:
    seq = (state.events[-1].sequence + 1) if state.events else 1
    state.events.append(
        SpeakingEvent(
            sequence=seq,
            event_type=event_type,
            session_id=state.session.session_id,
            at=at,
            attempt_id=attempt_id,
            turn_id=turn_id,
            detail=detail,
        )
    )


def _active_attempt(session: SpeakingSession) -> SpeakingAttempt | None:
    if not session.current_attempt_id:
        return None
    for attempt in session.attempts:
        if attempt.attempt_id == session.current_attempt_id:
            return attempt
    return None


def _replace_attempt(session: SpeakingSession, updated: SpeakingAttempt) -> SpeakingSession:
    attempts = tuple(updated if a.attempt_id == updated.attempt_id else a for a in session.attempts)
    if updated.attempt_id not in {a.attempt_id for a in session.attempts}:
        attempts = session.attempts + (updated,)
    return replace(session, attempts=attempts, current_attempt_id=updated.attempt_id)


def initialize(context: SpeakingContext, *, at: str | None = None, session_id: str | None = None) -> SpeakingState:
    """Lifecycle: initialize — create session in initialized status."""
    validate_context(context)
    targets = validate_grammar_targets(context.grammar_targets)
    ts = _now(at)
    session = SpeakingSession(
        session_id=session_id or _new_id("sspeak"),
        activity_id=context.activity_id,
        student_id=context.student_id,
        grammar_targets=targets,
        status=SpeakingSessionStatus.initialized,
        created_at=ts,
        updated_at=ts,
        language_id=context.language_id,
    )
    state = SpeakingState(session=session, context=context)
    state.phases_completed.append(SpeakingLifecyclePhase.initialize.value)
    _emit(state, SpeakingEventType.session_initialized, at=ts)
    validate_session_state(state.session)
    return state


def start_session(state: SpeakingState, *, at: str | None = None) -> SpeakingState:
    """Lifecycle: start_session — initialized → active."""
    ts = _now(at)
    assert_session_transition(state.session.status, SpeakingSessionStatus.active)
    state.session = replace(
        state.session,
        status=SpeakingSessionStatus.active,
        updated_at=ts,
    )
    state.phases_completed.append(SpeakingLifecyclePhase.start_session.value)
    _emit(state, SpeakingEventType.session_started, at=ts)
    return state


def start_attempt(state: SpeakingState, *, at: str | None = None) -> SpeakingState:
    """Lifecycle: start_attempt — create/activate a new attempt."""
    if state.session.status is not SpeakingSessionStatus.active:
        raise SpeakingLifecycleError(
            "session_not_active",
            f"start_attempt requires active session, got {state.session.status.value}",
        )
    current = _active_attempt(state.session)
    if current is not None and current.status is SpeakingAttemptStatus.active:
        raise SpeakingLifecycleError("attempt_already_active", current.attempt_id)

    ts = _now(at)
    number = len(state.session.attempts) + 1
    attempt = SpeakingAttempt(
        attempt_id=_new_id("sattempt"),
        session_id=state.session.session_id,
        attempt_number=number,
        status=SpeakingAttemptStatus.active,
        started_at=ts,
        finished_at="",
        turns=(),
    )
    assert_attempt_transition(SpeakingAttemptStatus.pending, SpeakingAttemptStatus.active)
    state.session = replace(
        _replace_attempt(state.session, attempt),
        updated_at=ts,
    )
    state.phases_completed.append(SpeakingLifecyclePhase.start_attempt.value)
    _emit(
        state,
        SpeakingEventType.attempt_started,
        at=ts,
        attempt_id=attempt.attempt_id,
        detail=f"attempt_number:{number}",
    )
    return state


def next_turn(
    state: SpeakingState,
    *,
    speaker: SpeakingSpeaker = SpeakingSpeaker.student,
    prompt_reference: str = "",
    student_response_reference: str = "",
    duration_ms: int = 0,
    close_previous: bool = True,
    at: str | None = None,
) -> SpeakingState:
    """Lifecycle: next_turn — open a new turn (optionally close previous open turn)."""
    attempt = _active_attempt(state.session)
    if attempt is None or attempt.status is not SpeakingAttemptStatus.active:
        raise SpeakingLifecycleError("no_active_attempt", "next_turn requires an active attempt")

    ts = _now(at)
    turns = list(attempt.turns)
    if close_previous and turns:
        last = turns[-1]
        if last.status is SpeakingTurnStatus.open:
            assert_turn_transition(last.status, SpeakingTurnStatus.closed)
            turns[-1] = replace(last, status=SpeakingTurnStatus.closed)
            _emit(
                state,
                SpeakingEventType.turn_closed,
                at=ts,
                attempt_id=attempt.attempt_id,
                turn_id=last.turn_id,
            )

    sequence = (turns[-1].sequence + 1) if turns else 1
    turn = SpeakingTurn(
        turn_id=_new_id("sturn"),
        speaker=speaker,
        sequence=sequence,
        prompt_reference=prompt_reference,
        student_response_reference=student_response_reference,
        duration_ms=max(0, duration_ms),
        status=SpeakingTurnStatus.open,
    )
    assert_turn_transition(SpeakingTurnStatus.pending, SpeakingTurnStatus.open)
    turns.append(turn)
    updated = replace(attempt, turns=tuple(turns))
    state.session = replace(_replace_attempt(state.session, updated), updated_at=ts)
    state.phases_completed.append(SpeakingLifecyclePhase.next_turn.value)
    _emit(
        state,
        SpeakingEventType.turn_opened,
        at=ts,
        attempt_id=attempt.attempt_id,
        turn_id=turn.turn_id,
        detail=f"sequence:{sequence}",
    )
    return state


def finish_attempt(
    state: SpeakingState,
    *,
    completion_state: SpeakingCompletionState = SpeakingCompletionState.complete,
    warnings: tuple[str, ...] = (),
    raw_outputs: dict[str, str] | None = None,
    at: str | None = None,
) -> SpeakingState:
    """Lifecycle: finish_attempt — close open turns and finish active attempt."""
    attempt = _active_attempt(state.session)
    if attempt is None or attempt.status is not SpeakingAttemptStatus.active:
        raise SpeakingLifecycleError("no_active_attempt", "finish_attempt requires an active attempt")

    ts = _now(at)
    turns = []
    for turn in attempt.turns:
        if turn.status is SpeakingTurnStatus.open:
            assert_turn_transition(turn.status, SpeakingTurnStatus.closed)
            closed = replace(turn, status=SpeakingTurnStatus.closed)
            turns.append(closed)
            _emit(
                state,
                SpeakingEventType.turn_closed,
                at=ts,
                attempt_id=attempt.attempt_id,
                turn_id=turn.turn_id,
            )
        else:
            turns.append(turn)

    assert_attempt_transition(attempt.status, SpeakingAttemptStatus.finished)
    finished = replace(
        attempt,
        status=SpeakingAttemptStatus.finished,
        finished_at=ts,
        turns=tuple(turns),
    )
    result = SpeakingResult(
        completion_state=completion_state,
        warnings=warnings,
        artifacts=(),
        timing=SpeakingTiming(started_at=attempt.started_at, finished_at=ts, duration_ms=0),
        raw_outputs=dict(raw_outputs or {}),
        notes=f"attempt:{finished.attempt_id}",
    )
    attempts = tuple(finished if a.attempt_id == finished.attempt_id else a for a in state.session.attempts)
    provisional = replace(
        state.session,
        attempts=attempts,
        current_attempt_id=finished.attempt_id,
        result=result,
        updated_at=ts,
    )
    evidence = build_speaking_evidence(
        provisional,
        attempt_id=finished.attempt_id,
        result=result,
    )
    state.session = replace(provisional, evidence=state.session.evidence + (evidence,))
    state.phases_completed.append(SpeakingLifecyclePhase.finish_attempt.value)
    _emit(
        state,
        SpeakingEventType.attempt_finished,
        at=ts,
        attempt_id=finished.attempt_id,
        detail=completion_state.value,
    )
    return state


def complete_session(state: SpeakingState, *, at: str | None = None) -> SpeakingState:
    """Lifecycle: complete_session — active → completing → completed."""
    if state.session.status is not SpeakingSessionStatus.active:
        raise SpeakingLifecycleError(
            "session_not_active",
            f"complete_session requires active session, got {state.session.status.value}",
        )
    active = _active_attempt(state.session)
    if active is not None and active.status is SpeakingAttemptStatus.active:
        raise SpeakingLifecycleError(
            "attempt_still_active",
            "finish_attempt before complete_session",
        )
    if state.session.result is None:
        raise SpeakingLifecycleError("missing_result", "complete_session requires SpeakingResult")

    ts = _now(at)
    assert_session_transition(state.session.status, SpeakingSessionStatus.completing)
    state.session = replace(state.session, status=SpeakingSessionStatus.completing, updated_at=ts)
    assert_session_transition(state.session.status, SpeakingSessionStatus.completed)
    state.session = replace(state.session, status=SpeakingSessionStatus.completed, updated_at=ts)
    state.phases_completed.append(SpeakingLifecyclePhase.complete_session.value)
    _emit(state, SpeakingEventType.session_completed, at=ts)
    validate_session_state(state.session)
    return state


def cancel(state: SpeakingState, *, reason: str = "", at: str | None = None) -> SpeakingState:
    """Lifecycle: cancel — cancel active attempt (if any) and session."""
    ts = _now(at)
    session = state.session
    attempt = _active_attempt(session)
    if attempt is not None and attempt.status is SpeakingAttemptStatus.active:
        assert_attempt_transition(attempt.status, SpeakingAttemptStatus.cancelled)
        cancelled_attempt = replace(attempt, status=SpeakingAttemptStatus.cancelled, finished_at=ts)
        session = _replace_attempt(session, cancelled_attempt)

    if session.status not in (
        SpeakingSessionStatus.completed,
        SpeakingSessionStatus.cancelled,
        SpeakingSessionStatus.failed,
    ):
        # Allow cancel from initialized or active (and completing via failed path not used)
        if session.status is SpeakingSessionStatus.initialized:
            assert_session_transition(session.status, SpeakingSessionStatus.cancelled)
        elif session.status is SpeakingSessionStatus.active:
            assert_session_transition(session.status, SpeakingSessionStatus.cancelled)
        elif session.status is SpeakingSessionStatus.completing:
            raise SpeakingStateError(
                "illegal_session_transition",
                f"{session.status.value} -> cancelled",
            )
        session = replace(
            session,
            status=SpeakingSessionStatus.cancelled,
            updated_at=ts,
            result=session.result
            or SpeakingResult(
                completion_state=SpeakingCompletionState.cancelled,
                warnings=(reason or "cancelled",),
                timing=SpeakingTiming(finished_at=ts),
            ),
        )
    state.session = session
    state.phases_completed.append(SpeakingLifecyclePhase.cancel.value)
    _emit(state, SpeakingEventType.session_cancelled, at=ts, detail=reason)
    return state


def to_view(state: SpeakingState) -> SpeakingSessionView:
    """Project SpeakingState to a public DTO."""
    observations = ()
    if state.session.evidence:
        # Map latest evidence envelope
        latest = state.session.evidence[-1]
        observations = map_speaking_evidence_to_observations(
            latest,
            context=state.context,
            observed_at=state.session.updated_at,
        )
    turn_count = sum(len(a.turns) for a in state.session.attempts)
    return SpeakingSessionView(
        session=state.session,
        status=state.session.status,
        attempt_count=len(state.session.attempts),
        turn_count=turn_count,
        current_attempt_id=state.session.current_attempt_id,
        events=tuple(state.events),
        mapped_observations=observations,
    )


def run_happy_path(
    context: SpeakingContext,
    *,
    at: str = "2026-01-01T00:00:00Z",
    turns: int = 2,
) -> SpeakingState:
    """Deterministic full lifecycle helper for tests (no audio/LLM)."""
    state = initialize(context, at=at)
    state = start_session(state, at=at)
    state = start_attempt(state, at=at)
    for index in range(turns):
        state = next_turn(
            state,
            speaker=SpeakingSpeaker.tutor if index % 2 == 0 else SpeakingSpeaker.student,
            prompt_reference=f"prompt_ref_{index}",
            student_response_reference=f"response_ref_{index}" if index % 2 else "",
            at=at,
        )
    state = finish_attempt(state, at=at)
    state = complete_session(state, at=at)
    return state
