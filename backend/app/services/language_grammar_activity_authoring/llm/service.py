"""LLM Activity Authoring orchestration (V1.4)."""

from __future__ import annotations

from app.services.language_grammar_activity_authoring.fingerprint import fingerprint_authoring_request
from app.services.language_grammar_activity_authoring.llm.errors import (
    LLMAuthoringError,
    LLMProviderError,
)
from app.services.language_grammar_activity_authoring.llm.fallback import fallback_to_placeholder
from app.services.language_grammar_activity_authoring.llm.flags import (
    configured_llm_authoring_provider_id,
    llm_authoring_enabled,
    llm_authoring_fallback_enabled,
    llm_authoring_retry_policy,
    llm_authoring_timeout_seconds,
)
from app.services.language_grammar_activity_authoring.llm.parser import parse_activity_specification_json
from app.services.language_grammar_activity_authoring.llm.prompt_builder import build_prompt_bundle
from app.services.language_grammar_activity_authoring.llm.registry import (
    LLMAuthoringProviderRegistry,
    get_default_llm_authoring_registry,
)
from app.services.language_grammar_activity_authoring.llm.retry import classify_exception, should_retry
from app.services.language_grammar_activity_authoring.llm.types import (
    LLMAuthoringAttempt,
    LLMAuthoringOutcome,
    LLMAuthoringProvider,
)
from app.services.language_grammar_activity_authoring.types import AuthoringRequest, AuthoringResult
from app.services.language_grammar_activity_authoring.validation import validate_authoring_request
from app.services.language_grammar_activity_spec import ActivitySpecification


def author_activity_with_llm_detailed(
    request: AuthoringRequest,
    *,
    provider: LLMAuthoringProvider | None = None,
    provider_id: str | None = None,
    registry: LLMAuthoringProviderRegistry | None = None,
    require_enabled: bool = False,
    allow_fallback: bool | None = None,
) -> LLMAuthoringOutcome:
    """Author via LLM provider; fall back to placeholder strategy on total failure."""
    if require_enabled and not llm_authoring_enabled():
        raise LLMAuthoringError(
            "llm_authoring_disabled",
            "LLM authoring disabled (LANG_GRAMMAR_LLM_AUTHORING_ENABLED)",
        )

    validate_authoring_request(request)

    reg = registry or get_default_llm_authoring_registry()
    resolved_id = (provider_id or configured_llm_authoring_provider_id()).strip().lower()
    active = provider or reg.get(resolved_id)
    active_id = getattr(active, "provider_id", resolved_id)
    provider_version = str(getattr(active, "provider_version", "1.0.0") or "1.0.0")

    prompts = build_prompt_bundle(
        request,
        provider_id=str(active_id),
        provider_version=provider_version,
    )
    policy = llm_authoring_retry_policy()
    timeout = llm_authoring_timeout_seconds()
    attempts: list[LLMAuthoringAttempt] = []
    last_error: BaseException | None = None

    for attempt_no in range(1, policy.max_attempts + 1):
        try:
            raw = active.generate_json(prompts, timeout_seconds=timeout)
            spec = parse_activity_specification_json(raw, request, provider_id=str(active_id))
            attempts.append(LLMAuthoringAttempt(attempt=attempt_no, reason="success"))
            return LLMAuthoringOutcome(
                specification=spec,
                provider_id=str(active_id),
                used_fallback=False,
                prompt_version=prompts.prompt_version,
                attempts=tuple(attempts),
                notes=f"llm:{active_id}:{spec.activity_type}",
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            reason = classify_exception(exc)
            attempts.append(
                LLMAuthoringAttempt(
                    attempt=attempt_no,
                    reason=reason,
                    detail=str(exc)[:200],
                )
            )
            if attempt_no < policy.max_attempts and should_retry(exc, policy):
                continue
            break

    detail = str(last_error) if last_error else "llm_failed"
    use_fallback = llm_authoring_fallback_enabled() if allow_fallback is None else allow_fallback
    if use_fallback:
        return fallback_to_placeholder(
            request,
            provider_id=str(active_id),
            attempts=tuple(attempts),
            detail=detail,
        )

    if isinstance(last_error, LLMAuthoringError):
        raise last_error
    raise LLMProviderError("llm_authoring_failed", detail) from last_error


def author_activity_with_llm(
    request: AuthoringRequest,
    *,
    provider: LLMAuthoringProvider | None = None,
    provider_id: str | None = None,
    registry: LLMAuthoringProviderRegistry | None = None,
    require_enabled: bool = False,
    allow_fallback: bool | None = None,
) -> ActivitySpecification:
    """Public content contract — ActivitySpecification only."""
    return author_activity_with_llm_detailed(
        request,
        provider=provider,
        provider_id=provider_id,
        registry=registry,
        require_enabled=require_enabled,
        allow_fallback=allow_fallback,
    ).specification


def llm_outcome_to_authoring_result(outcome: LLMAuthoringOutcome, request: AuthoringRequest) -> AuthoringResult:
    """Map LLM envelope into V1.3 AuthoringResult for callers that need it."""
    strategy_id = "placeholder_fallback" if outcome.used_fallback else f"llm:{outcome.provider_id}"
    return AuthoringResult(
        specification=outcome.specification,
        strategy_id=strategy_id,
        request_fingerprint=fingerprint_authoring_request(request),
        notes=outcome.notes,
    )
