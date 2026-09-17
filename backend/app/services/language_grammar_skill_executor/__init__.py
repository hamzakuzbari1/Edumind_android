"""Grammar Skill Execution Framework + Engine (G3.4 / V1.5).

RESPONSIBILITY: Execute ActivitySpecification via Registry plugins.
Owns execution session/lifecycle/evidence observations only.
Never writes Progression / Mastery / Review. Never owns Grammar or Authoring.
"""

from __future__ import annotations

from app.services.language_grammar_skill_executor.engine_validation import (
    validate_executor_available,
    validate_grammar_targets,
    validate_specification,
)
from app.services.language_grammar_skill_executor.errors import (
    BrokenSpecificationError,
    DuplicateExecutionIdError,
    MissingExecutorError,
    SkillExecutorDisabledError,
    SkillExecutorError,
)
from app.services.language_grammar_skill_executor.evidence_adapter import (
    adapt_execution_to_evidence,
    source_skill_for_executor,
)
from app.services.language_grammar_skill_executor.execution_service import (
    build_execution_context,
    cancel_execution,
    collect_evidence,
    complete_evaluation,
    create_execution,
    fail_execution,
    replay_execution,
    run_execution,
    start_execution,
    submit_student_response,
)
from app.services.language_grammar_skill_executor.flags import (
    grammar_engine_enabled,
    skill_execution_engine_enabled,
    skill_executor_enabled,
    skill_executor_strict,
    snapshot_feature_flags,
)
from app.services.language_grammar_skill_executor.lifecycle import (
    execute_activity,
    lifecycle_methods_present,
    run_lifecycle,
)
from app.services.language_grammar_skill_executor.plugin_loader import (
    load_builtin_plugins,
    load_plugins_from_factory_paths,
)
from app.services.language_grammar_skill_executor.plugins import (
    DEFAULT_ACTIVITY_TYPE_TO_EXECUTOR,
    REQUIRED_PLACEHOLDER_EXECUTOR_IDS,
    ConversationExecutor,
    FillBlankExecutor,
    GrammarExerciseExecutor,
    ListeningExecutor,
    MatchingExecutor,
    MultipleChoiceExecutor,
    OrderingExecutor,
    ReadingExecutor,
    SentenceBuilderExecutor,
    SpeakingExecutor,
    WritingExecutor,
    builtin_placeholder_executors,
)
from app.services.language_grammar_skill_executor.registry import (
    SkillExecutorRegistry,
    get_default_skill_executor_registry,
    reset_default_skill_executor_registry_for_tests,
)
from app.services.language_grammar_skill_executor.resolution import resolve_executor
from app.services.language_grammar_skill_executor.session import (
    ExecutionEngineState,
    ExecutionLifecycleEvent,
    ExecutionLifecycleEventType,
    ExecutionSession,
    SessionStatus,
    TERMINAL_SESSION_STATUSES,
)
from app.services.language_grammar_skill_executor.state_machine import (
    ALLOWED_TRANSITIONS,
    InvalidSessionTransitionError,
    assert_session_transition,
    can_transition,
)
from app.services.language_grammar_skill_executor.storage import (
    ExecutionSessionNotFoundError,
    ExecutionSessionStore,
    get_default_execution_session_store,
    reset_default_execution_session_store_for_tests,
)
from app.services.language_grammar_skill_executor.tracking import (
    ExecutionIdGuard,
    get_default_execution_id_guard,
    reset_default_execution_id_guard_for_tests,
)
from app.services.language_grammar_skill_executor.types import (
    GRAMMAR_SKILL_EXECUTOR_PACKAGE_VERSION,
    GRAMMAR_SKILL_EXECUTOR_SCHEMA_VERSION,
    CollectedOutput,
    CompletionState,
    ExecutionArtifact,
    ExecutionContext,
    ExecutionFeatureFlags,
    ExecutionMetadata,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTiming,
    ExecutorMetadata,
    LifecyclePhase,
    LIFECYCLE_PHASES,
    SkillExecutor,
    StudentContext,
    TeacherPersona,
)

PACKAGE_VERSION = GRAMMAR_SKILL_EXECUTOR_PACKAGE_VERSION
RESPONSIBILITY = (
    "Skill Execution Framework/Engine — execute ActivitySpecification via Registry; "
    "session lifecycle + evidence observations only; never Mastery/Progression/Review/Authoring"
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "DEFAULT_ACTIVITY_TYPE_TO_EXECUTOR",
    "GRAMMAR_SKILL_EXECUTOR_PACKAGE_VERSION",
    "GRAMMAR_SKILL_EXECUTOR_SCHEMA_VERSION",
    "LIFECYCLE_PHASES",
    "TERMINAL_SESSION_STATUSES",
    "BrokenSpecificationError",
    "CollectedOutput",
    "CompletionState",
    "ConversationExecutor",
    "DuplicateExecutionIdError",
    "ExecutionArtifact",
    "ExecutionContext",
    "ExecutionEngineState",
    "ExecutionFeatureFlags",
    "ExecutionIdGuard",
    "ExecutionLifecycleEvent",
    "ExecutionLifecycleEventType",
    "ExecutionMetadata",
    "ExecutionResult",
    "ExecutionSession",
    "ExecutionSessionNotFoundError",
    "ExecutionSessionStore",
    "ExecutionStatus",
    "ExecutionTiming",
    "ExecutorMetadata",
    "FillBlankExecutor",
    "GrammarExerciseExecutor",
    "InvalidSessionTransitionError",
    "LifecyclePhase",
    "ListeningExecutor",
    "MatchingExecutor",
    "MissingExecutorError",
    "MultipleChoiceExecutor",
    "OrderingExecutor",
    "PACKAGE_VERSION",
    "REQUIRED_PLACEHOLDER_EXECUTOR_IDS",
    "RESPONSIBILITY",
    "ReadingExecutor",
    "SentenceBuilderExecutor",
    "SessionStatus",
    "SkillExecutor",
    "SkillExecutorDisabledError",
    "SkillExecutorError",
    "SkillExecutorRegistry",
    "SpeakingExecutor",
    "StudentContext",
    "TeacherPersona",
    "WritingExecutor",
    "adapt_execution_to_evidence",
    "assert_session_transition",
    "build_execution_context",
    "builtin_placeholder_executors",
    "can_transition",
    "cancel_execution",
    "collect_evidence",
    "complete_evaluation",
    "create_execution",
    "execute_activity",
    "fail_execution",
    "get_default_execution_id_guard",
    "get_default_execution_session_store",
    "get_default_skill_executor_registry",
    "grammar_engine_enabled",
    "lifecycle_methods_present",
    "load_builtin_plugins",
    "load_plugins_from_factory_paths",
    "replay_execution",
    "reset_default_execution_id_guard_for_tests",
    "reset_default_execution_session_store_for_tests",
    "reset_default_skill_executor_registry_for_tests",
    "resolve_executor",
    "run_execution",
    "run_lifecycle",
    "skill_execution_engine_enabled",
    "skill_executor_enabled",
    "skill_executor_strict",
    "snapshot_feature_flags",
    "source_skill_for_executor",
    "start_execution",
    "submit_student_response",
    "validate_executor_available",
    "validate_grammar_targets",
    "validate_specification",
]
