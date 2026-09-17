"""Public Activity Authoring API (V1.3)."""

from __future__ import annotations

from app.services.language_grammar_activity_authoring.errors import (
    ActivityAuthoringError,
    AuthoringValidationError,
)
from app.services.language_grammar_activity_authoring.fingerprint import fingerprint_authoring_request
from app.services.language_grammar_activity_authoring.flags import (
    activity_authoring_enabled,
    activity_authoring_strict,
)
from app.services.language_grammar_activity_authoring.registry import (
    ActivityAuthoringRegistry,
    get_default_authoring_registry,
)
from app.services.language_grammar_activity_authoring.resolution import resolve_authoring_strategy
from app.services.language_grammar_activity_authoring.types import (
    AuthoringRequest,
    AuthoringResult,
)
from app.services.language_grammar_activity_authoring.validation import validate_authoring_request
from app.services.language_grammar_activity_spec import (
    ActivitySpecification,
    validate_activity_specification,
)


def author_activity_detailed(
    request: AuthoringRequest,
    *,
    registry: ActivityAuthoringRegistry | None = None,
    preferred_strategy_id: str | None = None,
    require_enabled: bool = False,
) -> AuthoringResult:
    """Author an activity; returns envelope whose content is ActivitySpecification only."""
    if require_enabled and not activity_authoring_enabled():
        raise ActivityAuthoringError(
            "authoring_disabled",
            "Activity authoring disabled (LANG_GRAMMAR_ACTIVITY_AUTHORING_ENABLED)",
        )

    validate_authoring_request(request)
    strategy = resolve_authoring_strategy(
        request,
        registry=registry or get_default_authoring_registry(),
        preferred_strategy_id=preferred_strategy_id,
    )
    specification = strategy.author(request)
    if not isinstance(specification, ActivitySpecification):
        raise ActivityAuthoringError(
            "invalid_authoring_output",
            "Strategy must return ActivitySpecification",
        )
    if activity_authoring_strict():
        validate_activity_specification(specification)

    req_targets = tuple(request.context.grammar_targets)
    if set(specification.grammar_targets) != set(req_targets):
        raise AuthoringValidationError(
            "grammar_target_mismatch",
            "Authored specification grammar_targets must come from the request",
        )
    if specification.grammar_topic not in req_targets:
        raise AuthoringValidationError(
            "grammar_topic_mismatch",
            "Authored grammar_topic must be one of request grammar_targets",
        )

    return AuthoringResult(
        specification=specification,
        strategy_id=strategy.strategy_id,
        request_fingerprint=fingerprint_authoring_request(request),
        notes=f"authored:{strategy.strategy_id}:{specification.activity_type}",
    )


def author_activity(
    request: AuthoringRequest,
    *,
    registry: ActivityAuthoringRegistry | None = None,
    preferred_strategy_id: str | None = None,
    require_enabled: bool = False,
) -> ActivitySpecification:
    """Author an activity — sole public content contract is ActivitySpecification."""
    return author_activity_detailed(
        request,
        registry=registry,
        preferred_strategy_id=preferred_strategy_id,
        require_enabled=require_enabled,
    ).specification
