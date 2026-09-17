"""Grammar Activity Provider Framework (G3.35.1).

RESPONSIBILITY: Provider interface, registry, and deterministic resolution.
Providers return ActivitySpecification only (canonical content contract).
"""

from __future__ import annotations

from app.services.language_grammar_activity_provider.flags import (
    configured_provider_id,
    grammar_engine_enabled,
)
from app.services.language_grammar_activity_provider.legacy import (
    ActivityResult,  # noqa: F401 — deprecated re-export
    legacy_activity_result_from_specification,
    specification_from_legacy_activity_result,
)
from app.services.language_grammar_activity_provider.providers import (
    CachedProvider,
    ClaudeProvider,
    FutureLLMProvider,
    TemplateProvider,
)
from app.services.language_grammar_activity_provider.registry import (
    GrammarActivityProviderRegistry,
    default_providers,
    get_default_provider_registry,
)
from app.services.language_grammar_activity_provider.resolution import (
    GrammarActivityProviderError,
    provide_activity,
    resolve_provider,
)
from app.services.language_grammar_activity_provider.spec_factory import build_activity_specification
from app.services.language_grammar_activity_provider.types import (
    GRAMMAR_ACTIVITY_PROVIDER_PACKAGE_VERSION,
    GRAMMAR_ACTIVITY_PROVIDER_SCHEMA_VERSION,
    ActivityExecutionContext,
    GrammarActivityProvider,
    GrammarActivityProviderId,
    GrammarRuntimeContext,
    GrammarStudentContext,
)
from app.services.language_grammar_activity_spec import ActivitySpecification

PACKAGE_VERSION = GRAMMAR_ACTIVITY_PROVIDER_PACKAGE_VERSION
RESPONSIBILITY = (
    "Activity Provider interface/registry/resolution — returns ActivitySpecification only"
)

__all__ = [
    "GRAMMAR_ACTIVITY_PROVIDER_PACKAGE_VERSION",
    "GRAMMAR_ACTIVITY_PROVIDER_SCHEMA_VERSION",
    "ActivityExecutionContext",
    "ActivityResult",  # deprecated
    "ActivitySpecification",
    "CachedProvider",
    "ClaudeProvider",
    "FutureLLMProvider",
    "GrammarActivityProvider",
    "GrammarActivityProviderError",
    "GrammarActivityProviderId",
    "GrammarActivityProviderRegistry",
    "GrammarRuntimeContext",
    "GrammarStudentContext",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "TemplateProvider",
    "build_activity_specification",
    "configured_provider_id",
    "default_providers",
    "get_default_provider_registry",
    "grammar_engine_enabled",
    "legacy_activity_result_from_specification",
    "provide_activity",
    "resolve_provider",
    "specification_from_legacy_activity_result",
]
