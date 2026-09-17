"""Activity Provider contracts (G3.35.1).

Providers sit between Runtime and content generation.
Claude is one future provider — never part of Runtime.
Providers return ActivitySpecification only — never Runtime state, UI, or markdown docs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from app.services.language_grammar_activity_spec import ActivitySpecification
from app.services.language_grammar_lesson_planner.types import (
    GrammarLessonBlueprint,
    GrammarLessonStep,
)

GRAMMAR_ACTIVITY_PROVIDER_SCHEMA_VERSION = 1
GRAMMAR_ACTIVITY_PROVIDER_PACKAGE_VERSION = "1.1.0"


class GrammarActivityProviderId(StrEnum):
    """Registered provider identifiers — selection is deterministic."""

    template = "template"
    cached = "cached"
    claude = "claude"
    future_llm = "future_llm"


@dataclass(frozen=True, slots=True)
class GrammarStudentContext:
    """Minimal student context for activity provision (no mastery/progression engines)."""

    student_id: int
    language_id: int
    overall_cefr: str = ""
    locale: str = "en"


@dataclass(frozen=True, slots=True)
class GrammarRuntimeContext:
    """Runtime-facing context snapshot — not mutable RuntimeSession state."""

    lesson_id: str
    grammar_id: str
    blueprint_fingerprint: str
    step_index: int
    completed_step_ids: tuple[str, ...] = ()
    as_of: str = ""


@dataclass(frozen=True, slots=True)
class ActivityExecutionContext:
    """Everything a provider may read — never Runtime state machines."""

    blueprint: GrammarLessonBlueprint
    step: GrammarLessonStep
    runtime: GrammarRuntimeContext
    student: GrammarStudentContext
    extras: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class GrammarActivityProvider(Protocol):
    """Provider interface — Runtime depends on this only."""

    @property
    def provider_id(self) -> GrammarActivityProviderId: ...

    def supports(self, context: ActivityExecutionContext) -> bool:
        """Whether this provider can serve the step (deterministic)."""
        ...

    def provide(self, context: ActivityExecutionContext) -> ActivitySpecification:
        """Return an ActivitySpecification. Never Runtime state. No LLM calls in stubs."""
        ...
