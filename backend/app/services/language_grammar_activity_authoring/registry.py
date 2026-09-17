"""Authoring Strategy Registry (V1.3) — deterministic, no switch chains."""

from __future__ import annotations

from app.services.language_grammar_activity_authoring.errors import AuthoringStrategyError
from app.services.language_grammar_activity_authoring.strategies import (
    DEFAULT_ACTIVITY_TYPE_TO_STRATEGY,
    builtin_authoring_strategies,
)
from app.services.language_grammar_activity_authoring.types import AuthoringStrategy


class ActivityAuthoringRegistry:
    """Registry of AuthoringStrategy plugins."""

    def __init__(
        self,
        strategies: tuple[AuthoringStrategy, ...] | None = None,
        *,
        activity_type_map: dict[str, str] | None = None,
    ) -> None:
        loaded = builtin_authoring_strategies() if strategies is None else strategies
        by_id: dict[str, AuthoringStrategy] = {}
        for strategy in loaded:
            sid = strategy.strategy_id
            if not sid or not str(sid).strip():
                raise AuthoringStrategyError("missing_strategy_id", "Strategy missing strategy_id")
            if sid in by_id:
                raise AuthoringStrategyError("duplicate_strategy_id", f"Duplicate strategy id: {sid}")
            by_id[sid] = strategy
        self._by_id = by_id
        self._activity_type_map = dict(activity_type_map or DEFAULT_ACTIVITY_TYPE_TO_STRATEGY)

    def get(self, strategy_id: str) -> AuthoringStrategy:
        strategy = self._by_id.get(strategy_id)
        if strategy is None:
            raise KeyError(f"Unknown authoring strategy: {strategy_id}")
        return strategy

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_id.keys()))

    def all_strategies(self) -> tuple[AuthoringStrategy, ...]:
        return tuple(self._by_id[i] for i in self.ids())

    def register(self, strategy: AuthoringStrategy) -> None:
        sid = strategy.strategy_id
        if sid in self._by_id:
            raise AuthoringStrategyError("duplicate_strategy_id", f"Duplicate strategy id: {sid}")
        self._by_id[sid] = strategy

    def map_activity_type(self, activity_type: str, strategy_id: str) -> None:
        if strategy_id not in self._by_id:
            raise AuthoringStrategyError("unknown_strategy", f"Cannot map unknown strategy: {strategy_id}")
        self._activity_type_map[activity_type] = strategy_id

    def preferred_strategy_id_for(self, activity_type: str) -> str | None:
        return self._activity_type_map.get(activity_type)

    def activity_type_map(self) -> dict[str, str]:
        return dict(self._activity_type_map)

    def find_supporting(self, activity_type: str) -> tuple[AuthoringStrategy, ...]:
        return tuple(s for s in self.all_strategies() if s.supports(activity_type))


_DEFAULT_REGISTRY: ActivityAuthoringRegistry | None = None


def get_default_authoring_registry() -> ActivityAuthoringRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = ActivityAuthoringRegistry()
    return _DEFAULT_REGISTRY


def reset_default_authoring_registry_for_tests() -> None:
    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = None
