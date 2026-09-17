"""LLM Activity Authoring Provider contracts (V1.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.services.language_grammar_activity_spec import ActivitySpecification

LLM_AUTHORING_PROMPT_VERSION = "1.7.0"
LLM_AUTHORING_PACKAGE_VERSION = "1.7.0"


@dataclass(frozen=True, slots=True)
class PromptBundle:
    """Prompt surfaces owned by Prompt Builder — providers never invent these."""

    system_prompt: str
    developer_prompt: str
    user_prompt: str
    prompt_version: str = LLM_AUTHORING_PROMPT_VERSION
    localization: str = "en"
    variables: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Configurable retry policy for LLM authoring."""

    max_attempts: int = 3
    retry_on_transient: bool = True
    retry_on_invalid_json: bool = True
    retry_on_schema_failure: bool = True
    retry_on_timeout: bool = True


@dataclass(frozen=True, slots=True)
class LLMAuthoringAttempt:
    """One attempt record for diagnostics (no execution state)."""

    attempt: int
    reason: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class LLMAuthoringOutcome:
    """Envelope — content contract remains ActivitySpecification only."""

    specification: ActivitySpecification
    provider_id: str
    used_fallback: bool = False
    prompt_version: str = LLM_AUTHORING_PROMPT_VERSION
    attempts: tuple[LLMAuthoringAttempt, ...] = ()
    notes: str = ""


@runtime_checkable
class LLMAuthoringProvider(Protocol):
    """LLM authoring adapter — content generation only."""

    @property
    def provider_id(self) -> str: ...

    def generate_json(
        self,
        prompts: PromptBundle,
        *,
        timeout_seconds: float,
    ) -> str:
        """Return structured JSON text for ActivitySpecification. No UI. No mastery."""
        ...
