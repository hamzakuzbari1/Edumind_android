"""Execution ID guard — reject duplicate execution_ids within a scope (G3.4)."""

from __future__ import annotations

from app.services.language_grammar_skill_executor.errors import DuplicateExecutionIdError


class ExecutionIdGuard:
    """In-memory deterministic duplicate detection for a runner scope."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def claim(self, execution_id: str) -> None:
        eid = (execution_id or "").strip()
        if not eid:
            raise DuplicateExecutionIdError("Missing execution_id")
        if eid in self._seen:
            raise DuplicateExecutionIdError(f"Duplicate execution_id: {eid}")
        self._seen.add(eid)

    def contains(self, execution_id: str) -> bool:
        return execution_id in self._seen

    def clear(self) -> None:
        self._seen.clear()


_DEFAULT_GUARD = ExecutionIdGuard()


def get_default_execution_id_guard() -> ExecutionIdGuard:
    return _DEFAULT_GUARD


def reset_default_execution_id_guard_for_tests() -> None:
    _DEFAULT_GUARD.clear()
