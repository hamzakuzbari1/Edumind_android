"""In-memory Execution Session store for replayability (V1.5)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_grammar_skill_executor.errors import SkillExecutorError
from app.services.language_grammar_skill_executor.session import ExecutionEngineState


class ExecutionSessionNotFoundError(SkillExecutorError):
    """Unknown execution_session_id."""


@dataclass
class ExecutionSessionStore:
    """Process-local store — snapshots enable replay without re-running executors."""

    _sessions: dict[str, ExecutionEngineState] = field(default_factory=dict)

    def save(self, state: ExecutionEngineState) -> None:
        # Deep-ish copy of mutable lists so later mutations don't rewrite history.
        snap = ExecutionEngineState(
            session=state.session,
            context=state.context,
            specification=state.specification,
            events=list(state.events),
            result=state.result,
            observations=tuple(state.observations),
            status_history=list(status for status in state.status_history),
            snapshot_version=state.snapshot_version,
        )
        self._sessions[state.session.execution_session_id] = snap

    def get(self, execution_session_id: str) -> ExecutionEngineState:
        state = self._sessions.get(execution_session_id)
        if state is None:
            raise ExecutionSessionNotFoundError(
                f"Unknown execution_session_id: {execution_session_id}"
            )
        return ExecutionEngineState(
            session=state.session,
            context=state.context,
            specification=state.specification,
            events=list(state.events),
            result=state.result,
            observations=tuple(state.observations),
            status_history=list(state.status_history),
            snapshot_version=state.snapshot_version,
        )

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._sessions.keys()))

    def clear(self) -> None:
        self._sessions.clear()


_DEFAULT_STORE: ExecutionSessionStore | None = None


def get_default_execution_session_store() -> ExecutionSessionStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = ExecutionSessionStore()
    return _DEFAULT_STORE


def reset_default_execution_session_store_for_tests() -> None:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is not None:
        _DEFAULT_STORE.clear()
    _DEFAULT_STORE = None
