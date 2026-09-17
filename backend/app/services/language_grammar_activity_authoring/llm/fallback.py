"""Deterministic placeholder fallback when LLM authoring fails (V1.4)."""

from __future__ import annotations

from dataclasses import replace

from app.services.language_grammar_activity_authoring.author import author_activity_detailed
from app.services.language_grammar_activity_authoring.llm.types import (
    LLMAuthoringAttempt,
    LLMAuthoringOutcome,
)
from app.services.language_grammar_activity_authoring.types import AuthoringRequest
from app.services.language_grammar_activity_spec import ProviderMetadata, with_fingerprint


def fallback_to_placeholder(
    request: AuthoringRequest,
    *,
    provider_id: str,
    attempts: tuple[LLMAuthoringAttempt, ...] = (),
    detail: str = "",
) -> LLMAuthoringOutcome:
    """Activate V1.3 placeholder strategy so the system continues functioning."""
    result = author_activity_detailed(request)
    meta = ProviderMetadata(
        provider_id="authoring_placeholder",
        provider_version=result.specification.provider_metadata.provider_version or "1.0.0",
        generation_mode="authoring_placeholder_fallback",
        extras={
            **dict(result.specification.provider_metadata.extras),
            "fallback_from": provider_id,
            "fallback_reason": (detail or "llm_failed")[:200],
        },
    )
    patched = with_fingerprint(replace(result.specification, provider_metadata=meta))
    return LLMAuthoringOutcome(
        specification=patched,
        provider_id=provider_id,
        used_fallback=True,
        attempts=attempts,
        notes=f"fallback:placeholder:from={provider_id}:{(detail or 'llm_failed')}"[:240],
    )
