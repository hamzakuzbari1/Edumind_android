"""Deterministic provider resolution (G3.35.1) — returns ActivitySpecification."""

from __future__ import annotations

from app.services.language_grammar_activity_provider.flags import configured_provider_id
from app.services.language_grammar_activity_provider.registry import (
    GrammarActivityProviderRegistry,
    get_default_provider_registry,
)
from app.services.language_grammar_activity_provider.types import (
    ActivityExecutionContext,
    GrammarActivityProvider,
    GrammarActivityProviderId,
)
from app.services.language_grammar_activity_spec import ActivitySpecification


class GrammarActivityProviderError(ValueError):
    """Invalid provider selection or provision."""


def resolve_provider(
    context: ActivityExecutionContext,
    *,
    registry: GrammarActivityProviderRegistry | None = None,
    preferred: GrammarActivityProviderId | None = None,
) -> GrammarActivityProvider:
    """Select a provider deterministically."""
    reg = registry or get_default_provider_registry()
    candidates: list[GrammarActivityProviderId] = []
    if preferred is not None:
        candidates.append(preferred)
    configured = configured_provider_id()
    if configured not in candidates:
        candidates.append(configured)
    if GrammarActivityProviderId.template not in candidates:
        candidates.append(GrammarActivityProviderId.template)

    for pid in candidates:
        try:
            provider = reg.get(pid)
        except KeyError:
            continue
        if provider.supports(context):
            return provider
    raise GrammarActivityProviderError("No activity provider supports this context")


def provide_activity(
    context: ActivityExecutionContext,
    *,
    registry: GrammarActivityProviderRegistry | None = None,
    preferred: GrammarActivityProviderId | None = None,
) -> ActivitySpecification:
    """Resolve provider and return ActivitySpecification — sole content contract."""
    provider = resolve_provider(context, registry=registry, preferred=preferred)
    result = provider.provide(context)
    if not isinstance(result, ActivitySpecification):
        raise GrammarActivityProviderError(
            "Provider must return ActivitySpecification (ActivityResult is deprecated)"
        )
    if result.step_id != context.step.step_id:
        raise GrammarActivityProviderError("Provider returned mismatched step_id")
    if result.provider_metadata.provider_id != provider.provider_id.value:
        raise GrammarActivityProviderError("Provider returned mismatched provider_id")
    return result
