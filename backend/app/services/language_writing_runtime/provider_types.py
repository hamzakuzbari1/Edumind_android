"""WritingModelProvider types (W6) — provider abstraction; Claude accessed only through generate()."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing_generation.prompt_builder_types import WritingPromptBundle

PROVIDER_CONTRACT_VERSION = "6.0.0"


@dataclass(frozen=True, slots=True)
class ModelCapabilityFlags:
    """Future provider capability flags — architecture contract."""

    supports_json_mode: bool = True
    supports_streaming: bool = False
    supports_vision: bool = False
    supports_local_inference: bool = False
    provider_family: str = "claude"


@dataclass(frozen=True, slots=True)
class WritingModelGenerateRequest:
    """Provider input — prompt bundle only; no blueprint, student, or progression."""

    prompt_bundle: WritingPromptBundle
    locale: str = "en"


@dataclass(frozen=True, slots=True)
class WritingModelGenerateResponse:
    """Raw provider output — no post-processing."""

    raw_text: str
    provider_name: str
    model_name: str
    llm_version: str
    duration_ms: int
    temperature: float
    max_tokens: int


@dataclass(frozen=True, slots=True)
class WritingModelProviderInfo:
    provider_name: str
    model_name: str
    temperature: float
    max_tokens: int
    capabilities: ModelCapabilityFlags = field(default_factory=ModelCapabilityFlags)
