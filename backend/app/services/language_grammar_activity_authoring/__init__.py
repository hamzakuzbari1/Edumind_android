"""Grammar Activity Authoring Framework (V1.3 + V1.4 LLM Provider).

RESPONSIBILITY: Generate ActivitySpecification from Grammar Targets.
Grammar is the sole learning-goal source of truth. LLM authors content only.
No Runtime or Skill execution ownership.
"""

from __future__ import annotations

from app.services.language_grammar_activity_authoring.author import (
    author_activity,
    author_activity_detailed,
)
from app.services.language_grammar_activity_authoring.llm import (
    ClaudeAuthoringProvider,
    LLMAuthoringOutcome,
    LLMAuthoringProvider,
    LLMAuthoringProviderRegistry,
    PromptBundle,
    RetryPolicy,
    author_activity_with_llm,
    author_activity_with_llm_detailed,
    build_prompt_bundle,
    get_default_llm_authoring_registry,
    llm_authoring_enabled,
    parse_activity_specification_json,
)
from app.services.language_grammar_activity_authoring.errors import (
    ActivityAuthoringError,
    AuthoringStrategyError,
    AuthoringValidationError,
)
from app.services.language_grammar_activity_authoring.fingerprint import fingerprint_authoring_request
from app.services.language_grammar_activity_authoring.flags import (
    activity_authoring_enabled,
    activity_authoring_strict,
    grammar_engine_enabled,
)
from app.services.language_grammar_activity_authoring.registry import (
    ActivityAuthoringRegistry,
    get_default_authoring_registry,
    reset_default_authoring_registry_for_tests,
)
from app.services.language_grammar_activity_authoring.resolution import resolve_authoring_strategy
from app.services.language_grammar_activity_authoring.strategies import (
    DEFAULT_ACTIVITY_TYPE_TO_STRATEGY,
    REQUIRED_AUTHORING_STRATEGY_IDS,
    ConversationAuthoringStrategy,
    FillBlankAuthoringStrategy,
    GrammarExerciseAuthoringStrategy,
    ListeningAuthoringStrategy,
    MatchingAuthoringStrategy,
    MultipleChoiceAuthoringStrategy,
    OrderingAuthoringStrategy,
    ReadingAuthoringStrategy,
    SentenceBuilderAuthoringStrategy,
    SpeakingAuthoringStrategy,
    WritingAuthoringStrategy,
    builtin_authoring_strategies,
)
from app.services.language_grammar_activity_authoring.adaptive import (
    ADAPTIVE_AUTHORING_PACKAGE_VERSION,
    ADAPTIVE_SNAPSHOT_SCHEMA_VERSION,
    AdaptiveAuthoringContext,
    RecentErrorSummary,
    StudentLearningSnapshot,
    empty_learning_snapshot,
    learning_snapshot_from_mapping,
)
from app.services.language_grammar_activity_authoring.types import (
    GRAMMAR_ACTIVITY_AUTHORING_PACKAGE_VERSION,
    GRAMMAR_ACTIVITY_AUTHORING_SCHEMA_VERSION,
    AuthoringContext,
    AuthoringRequest,
    AuthoringResult,
    AuthoringStrategy,
    AuthoringVersionBundle,
    LessonContext,
    StudentProfile,
    TeacherPersona,
)
from app.services.language_grammar_activity_authoring.validation import validate_authoring_request
from app.services.language_grammar_activity_spec import ActivitySpecification

PACKAGE_VERSION = GRAMMAR_ACTIVITY_AUTHORING_PACKAGE_VERSION
RESPONSIBILITY = (
    "Activity Authoring Framework - generate adaptive ActivitySpecification lessons from "
    "Grammar Targets + learning snapshot (HOW only); never invent curriculum; "
    "no Runtime/Skill/Mastery ownership"
)

__all__ = [
    "ADAPTIVE_AUTHORING_PACKAGE_VERSION",
    "ADAPTIVE_SNAPSHOT_SCHEMA_VERSION",
    "DEFAULT_ACTIVITY_TYPE_TO_STRATEGY",
    "GRAMMAR_ACTIVITY_AUTHORING_PACKAGE_VERSION",
    "GRAMMAR_ACTIVITY_AUTHORING_SCHEMA_VERSION",
    "PACKAGE_VERSION",
    "REQUIRED_AUTHORING_STRATEGY_IDS",
    "RESPONSIBILITY",
    "ActivityAuthoringError",
    "ActivityAuthoringRegistry",
    "ActivitySpecification",
    "AdaptiveAuthoringContext",
    "AuthoringContext",
    "AuthoringRequest",
    "AuthoringResult",
    "AuthoringStrategy",
    "AuthoringStrategyError",
    "AuthoringValidationError",
    "AuthoringVersionBundle",
    "ConversationAuthoringStrategy",
    "FillBlankAuthoringStrategy",
    "GrammarExerciseAuthoringStrategy",
    "LessonContext",
    "ListeningAuthoringStrategy",
    "MatchingAuthoringStrategy",
    "MultipleChoiceAuthoringStrategy",
    "OrderingAuthoringStrategy",
    "ReadingAuthoringStrategy",
    "RecentErrorSummary",
    "SentenceBuilderAuthoringStrategy",
    "SpeakingAuthoringStrategy",
    "StudentLearningSnapshot",
    "StudentProfile",
    "TeacherPersona",
    "WritingAuthoringStrategy",
    "ClaudeAuthoringProvider",
    "LLMAuthoringOutcome",
    "LLMAuthoringProvider",
    "LLMAuthoringProviderRegistry",
    "PromptBundle",
    "RetryPolicy",
    "activity_authoring_enabled",
    "activity_authoring_strict",
    "author_activity",
    "author_activity_detailed",
    "author_activity_with_llm",
    "author_activity_with_llm_detailed",
    "build_prompt_bundle",
    "builtin_authoring_strategies",
    "empty_learning_snapshot",
    "fingerprint_authoring_request",
    "get_default_authoring_registry",
    "get_default_llm_authoring_registry",
    "grammar_engine_enabled",
    "learning_snapshot_from_mapping",
    "llm_authoring_enabled",
    "parse_activity_specification_json",
    "reset_default_authoring_registry_for_tests",
    "resolve_authoring_strategy",
    "validate_authoring_request",
]
