"""Skill Executor Registry (G3.4) — Runtime discovers executors only here."""

from __future__ import annotations

from app.services.language_grammar_skill_executor.errors import SkillExecutorError
from app.services.language_grammar_skill_executor.plugin_loader import load_builtin_plugins
from app.services.language_grammar_skill_executor.plugins import DEFAULT_ACTIVITY_TYPE_TO_EXECUTOR
from app.services.language_grammar_skill_executor.types import SkillExecutor


class SkillExecutorRegistry:
    """Deterministic registry of SkillExecutor plugins.

    No Runtime if-activity branching — resolution is registry-driven.
    """

    def __init__(
        self,
        executors: tuple[SkillExecutor, ...] | None = None,
        *,
        activity_type_map: dict[str, str] | None = None,
    ) -> None:
        # Use `is None` so an explicit empty tuple stays empty (falsy `()` must not load builtins).
        self._executors: tuple[SkillExecutor, ...] = (
            load_builtin_plugins() if executors is None else executors
        )
        by_id: dict[str, SkillExecutor] = {}
        for executor in self._executors:
            eid = executor.executor_id
            if not eid or not str(eid).strip():
                raise SkillExecutorError("Executor missing executor_id")
            if eid in by_id:
                raise SkillExecutorError(f"Duplicate executor id: {eid}")
            by_id[eid] = executor
        self._by_id = by_id
        self._activity_type_map = dict(activity_type_map or DEFAULT_ACTIVITY_TYPE_TO_EXECUTOR)

    def get(self, executor_id: str) -> SkillExecutor:
        executor = self._by_id.get(executor_id)
        if executor is None:
            raise KeyError(f"Unknown skill executor: {executor_id}")
        return executor

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_id.keys()))

    def all_executors(self) -> tuple[SkillExecutor, ...]:
        return tuple(self._by_id[i] for i in self.ids())

    def register(self, executor: SkillExecutor) -> None:
        """Register an additional plugin — no Runtime / Planner / Provider edits required."""
        eid = executor.executor_id
        if eid in self._by_id:
            raise SkillExecutorError(f"Duplicate executor id: {eid}")
        self._by_id[eid] = executor

    def map_activity_type(self, activity_type: str, executor_id: str) -> None:
        """Extend activity_type → executor mapping without touching Runtime."""
        if executor_id not in self._by_id:
            raise SkillExecutorError(f"Cannot map unknown executor: {executor_id}")
        self._activity_type_map[activity_type] = executor_id

    def preferred_executor_id_for(self, activity_type: str) -> str | None:
        return self._activity_type_map.get(activity_type)

    def activity_type_map(self) -> dict[str, str]:
        return dict(self._activity_type_map)

    def find_supporting(self, activity_type: str) -> tuple[SkillExecutor, ...]:
        return tuple(e for e in self.all_executors() if e.supports(activity_type))


_DEFAULT_REGISTRY: SkillExecutorRegistry | None = None


def get_default_skill_executor_registry() -> SkillExecutorRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = SkillExecutorRegistry()
    return _DEFAULT_REGISTRY


def reset_default_skill_executor_registry_for_tests() -> None:
    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = None
