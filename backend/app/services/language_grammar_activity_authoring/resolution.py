"""Deterministic authoring strategy resolution (V1.3)."""

from __future__ import annotations

from app.services.language_grammar_activity_authoring.errors import AuthoringStrategyError
from app.services.language_grammar_activity_authoring.registry import (
    ActivityAuthoringRegistry,
    get_default_authoring_registry,
)
from app.services.language_grammar_activity_authoring.types import AuthoringRequest, AuthoringStrategy


def resolve_authoring_strategy(
    request: AuthoringRequest,
    *,
    registry: ActivityAuthoringRegistry | None = None,
    preferred_strategy_id: str | None = None,
) -> AuthoringStrategy:
    """Resolve strategy from activity type via Registry — no switch statements."""
    reg = registry or get_default_authoring_registry()
    activity_type = request.context.activity_type
    preferred = (
        preferred_strategy_id or request.context.preferred_strategy_id or ""
    ).strip()

    if preferred:
        try:
            return reg.get(preferred)
        except KeyError as exc:
            raise AuthoringStrategyError(
                "missing_strategy",
                f"Preferred strategy not registered: {preferred}",
            ) from exc

    mapped = reg.preferred_strategy_id_for(activity_type)
    if mapped:
        try:
            strategy = reg.get(mapped)
        except KeyError as exc:
            raise AuthoringStrategyError(
                "missing_strategy",
                f"Mapped strategy not registered for {activity_type}: {mapped}",
            ) from exc
        if strategy.supports(activity_type):
            return strategy

    supporting = reg.find_supporting(activity_type)
    if supporting:
        return supporting[0]

    raise AuthoringStrategyError(
        "missing_strategy",
        f"No authoring strategy registered for activity_type={activity_type!r}",
    )
