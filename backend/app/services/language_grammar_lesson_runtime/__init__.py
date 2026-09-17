"""Grammar Lesson Runtime (V1.1) — executes frozen GrammarLessonBlueprint only.

RESPONSIBILITY: Cursor / step dispatch / events / persistence.
Activity execution goes exclusively through Skill Executor Registry.
Never plans lessons, never scores mastery, never schedules review, never calls Claude.
"""

from __future__ import annotations

from app.services.language_grammar_lesson_runtime.dispatcher import GrammarRuntimeError, dispatch_step
from app.services.language_grammar_lesson_runtime.executors import (
    GrammarExecutorRegistry,
    get_default_registry,
)
from app.services.language_grammar_lesson_runtime.flags import (
    grammar_engine_enabled,
    grammar_engine_select_enabled,
)
from app.services.language_grammar_lesson_runtime.orchestrator import (
    cancel,
    complete_current_step,
    create_session,
    fail,
    pause,
    prepare,
    resume,
    run_to_completion,
    start,
    to_view,
)
from app.services.language_grammar_lesson_runtime.service import (
    execute_blueprint,
    load_session,
    persist_session,
)
from app.services.language_grammar_lesson_runtime.skill_execution_bridge import (
    SkillExecutionBridgeError,
    run_skill_execution,
)
from app.services.language_grammar_lesson_runtime.types import (
    GRAMMAR_RUNTIME_SCHEMA_VERSION,
    GRAMMAR_RUNTIME_VERSION,
    ALLOWED_TRANSITIONS,
    GrammarEvidenceRequest,
    GrammarRuntimeCursor,
    GrammarRuntimeEvent,
    GrammarRuntimeEventType,
    GrammarRuntimeLifecycle,
    GrammarRuntimeSession,
    GrammarRuntimeState,
    GrammarRuntimeView,
    GrammarStepExecutionRecord,
)

PACKAGE_VERSION = GRAMMAR_RUNTIME_VERSION
RESPONSIBILITY = (
    "Execute Blueprint.steps via Provider Spec + Skill Executor Registry; "
    "never decide lesson ordering"
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "GRAMMAR_RUNTIME_SCHEMA_VERSION",
    "GRAMMAR_RUNTIME_VERSION",
    "GrammarEvidenceRequest",
    "GrammarExecutorRegistry",
    "GrammarRuntimeCursor",
    "GrammarRuntimeError",
    "GrammarRuntimeEvent",
    "GrammarRuntimeEventType",
    "GrammarRuntimeLifecycle",
    "GrammarRuntimeSession",
    "GrammarRuntimeState",
    "GrammarRuntimeView",
    "GrammarStepExecutionRecord",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "SkillExecutionBridgeError",
    "cancel",
    "complete_current_step",
    "create_session",
    "dispatch_step",
    "execute_blueprint",
    "fail",
    "get_default_registry",
    "grammar_engine_enabled",
    "grammar_engine_select_enabled",
    "load_session",
    "pause",
    "persist_session",
    "prepare",
    "resume",
    "run_skill_execution",
    "run_to_completion",
    "start",
    "to_view",
]
