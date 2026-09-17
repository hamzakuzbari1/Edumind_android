"""LLM Activity Authoring Provider (V1.4 / V1.6 Grammar-Aware Lessons).

RESPONSIBILITY: Generate ActivitySpecification lesson content via LLM adapters.
LLM teaches only provided Grammar Targets — never invents curriculum.
Never owns Progression/Mastery/Review/Runtime/Skill Execution.
"""

from __future__ import annotations

from app.services.language_grammar_activity_authoring.llm.errors import (
    LLMAuthoringError,
    LLMInvalidJSONError,
    LLMProviderError,
    LLMSchemaError,
    LLMTimeoutError,
    LLMTransientError,
)
from app.services.language_grammar_activity_authoring.llm.flags import (
    configured_llm_authoring_provider_id,
    llm_authoring_enabled,
    llm_authoring_fallback_enabled,
    llm_authoring_retry_policy,
    llm_authoring_timeout_seconds,
)
from app.services.language_grammar_activity_authoring.llm.lesson_schema import (
    ALL_REQUIRED_LESSON_SECTIONS,
    LESSON_PACKAGE_VERSION,
    LESSON_SCHEMA_VERSION,
    REQUIRED_LESSON_SECTIONS,
    REQUIRED_PERSONALIZATION_SECTIONS,
    CommonMistakeExample,
    GrammarLessonPackage,
    lesson_package_from_specification_payload,
    lesson_package_to_payload,
)
from app.services.language_grammar_activity_authoring.llm.lesson_validation import (
    detect_unsupported_grammar,
    validate_adaptive_personalization,
    validate_grammar_fidelity,
    validate_lesson_package_shape,
)
from app.services.language_grammar_activity_authoring.llm.parser import (
    extract_json_object,
    parse_activity_specification_json,
)
from app.services.language_grammar_activity_authoring.llm.prompt_builder import build_prompt_bundle
from app.services.language_grammar_activity_authoring.llm.providers import (
    ClaudeAuthoringProvider,
    GeminiAuthoringProvider,
    GPTAuthoringProvider,
    LocalModelAuthoringProvider,
    builtin_llm_authoring_providers,
)
from app.services.language_grammar_activity_authoring.llm.registry import (
    LLMAuthoringProviderRegistry,
    get_default_llm_authoring_registry,
    reset_default_llm_authoring_registry_for_tests,
)
from app.services.language_grammar_activity_authoring.llm.service import (
    author_activity_with_llm,
    author_activity_with_llm_detailed,
    llm_outcome_to_authoring_result,
)
from app.services.language_grammar_activity_authoring.llm.templates import PROMPT_VERSION
from app.services.language_grammar_activity_authoring.llm.types import (
    LLM_AUTHORING_PACKAGE_VERSION,
    LLM_AUTHORING_PROMPT_VERSION,
    LLMAuthoringAttempt,
    LLMAuthoringOutcome,
    LLMAuthoringProvider,
    PromptBundle,
    RetryPolicy,
)

PACKAGE_VERSION = LLM_AUTHORING_PACKAGE_VERSION
RESPONSIBILITY = (
    "LLM Adaptive Grammar Lesson Authoring — personalize lesson packages from "
    "Grammar Targets + learning snapshot (HOW only); never invent curriculum"
)

__all__ = [
    "ALL_REQUIRED_LESSON_SECTIONS",
    "LESSON_PACKAGE_VERSION",
    "LESSON_SCHEMA_VERSION",
    "LLM_AUTHORING_PACKAGE_VERSION",
    "LLM_AUTHORING_PROMPT_VERSION",
    "PACKAGE_VERSION",
    "PROMPT_VERSION",
    "REQUIRED_LESSON_SECTIONS",
    "REQUIRED_PERSONALIZATION_SECTIONS",
    "RESPONSIBILITY",
    "ClaudeAuthoringProvider",
    "CommonMistakeExample",
    "GeminiAuthoringProvider",
    "GPTAuthoringProvider",
    "GrammarLessonPackage",
    "LLMAuthoringAttempt",
    "LLMAuthoringError",
    "LLMAuthoringOutcome",
    "LLMAuthoringProvider",
    "LLMAuthoringProviderRegistry",
    "LLMInvalidJSONError",
    "LLMProviderError",
    "LLMSchemaError",
    "LLMTimeoutError",
    "LLMTransientError",
    "LocalModelAuthoringProvider",
    "PromptBundle",
    "RetryPolicy",
    "author_activity_with_llm",
    "author_activity_with_llm_detailed",
    "build_prompt_bundle",
    "builtin_llm_authoring_providers",
    "configured_llm_authoring_provider_id",
    "detect_unsupported_grammar",
    "extract_json_object",
    "get_default_llm_authoring_registry",
    "lesson_package_from_specification_payload",
    "lesson_package_to_payload",
    "llm_authoring_enabled",
    "llm_authoring_fallback_enabled",
    "llm_authoring_retry_policy",
    "llm_authoring_timeout_seconds",
    "llm_outcome_to_authoring_result",
    "parse_activity_specification_json",
    "reset_default_llm_authoring_registry_for_tests",
    "validate_adaptive_personalization",
    "validate_grammar_fidelity",
    "validate_lesson_package_shape",
]
