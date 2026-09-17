"""Deterministic plugin loading for Skill Executors (G3.4)."""

from __future__ import annotations

import importlib
from collections.abc import Callable, Sequence
from typing import Any

from app.services.language_grammar_skill_executor.errors import SkillExecutorError
from app.services.language_grammar_skill_executor.plugins import builtin_placeholder_executors
from app.services.language_grammar_skill_executor.types import SkillExecutor


def load_builtin_plugins() -> tuple[SkillExecutor, ...]:
    """Load the deterministic builtin placeholder plugin set."""
    return tuple(builtin_placeholder_executors())


def load_plugins_from_factory_paths(
    factory_paths: Sequence[str],
) -> tuple[SkillExecutor, ...]:
    """Load plugins from ``module:attr`` factory paths (deterministic order).

    Each factory must be a zero-arg callable returning SkillExecutor or a sequence
    of SkillExecutor instances. No Runtime / Planner / Provider coupling.
    """
    loaded: list[SkillExecutor] = []
    for path in factory_paths:
        loaded.extend(_load_one_factory(path))
    return tuple(loaded)


def _load_one_factory(path: str) -> list[SkillExecutor]:
    if ":" not in path:
        raise SkillExecutorError(f"Invalid plugin factory path (expected module:attr): {path}")
    module_name, attr_name = path.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise SkillExecutorError(f"Cannot import plugin module: {module_name}") from exc
    factory: Any = getattr(module, attr_name, None)
    if factory is None:
        raise SkillExecutorError(f"Plugin factory not found: {path}")
    if not callable(factory):
        raise SkillExecutorError(f"Plugin factory is not callable: {path}")
    return _normalize_factory_result(factory)


def _normalize_factory_result(factory: Callable[[], Any]) -> list[SkillExecutor]:
    result = factory()
    if isinstance(result, SkillExecutor):
        return [result]
    if isinstance(result, (list, tuple)):
        out: list[SkillExecutor] = []
        for item in result:
            if not isinstance(item, SkillExecutor):
                raise SkillExecutorError("Plugin factory returned non-SkillExecutor item")
            out.append(item)
        return out
    raise SkillExecutorError("Plugin factory must return SkillExecutor or sequence thereof")
