"""Grammar Activity Authoring contracts (V1.3 / V1.7 adaptive).

Authoring generates ActivitySpecification from Grammar Targets only.
Adaptive snapshot influences HOW lessons are taught — never WHAT grammar.
No Runtime state, Skill state, UI, or LLM calls in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.services.language_grammar_activity_authoring.adaptive import (
    AdaptiveAuthoringContext,
    StudentLearningSnapshot,
)
from app.services.language_grammar_activity_spec import (
    ActivityDifficulty,
    ActivitySpecification,
)

GRAMMAR_ACTIVITY_AUTHORING_SCHEMA_VERSION = 1
GRAMMAR_ACTIVITY_AUTHORING_PACKAGE_VERSION = "1.7.0"


@dataclass(frozen=True, slots=True)
class AuthoringVersionBundle:
    """Replayability versions — mandatory on every authoring request."""

    catalog_version: str
    grammar_schema_version: int
    blueprint_version: str
    activity_schema_version: int
    planner_version: str
    provider_version: str = "authoring"
    authoring_version: str = GRAMMAR_ACTIVITY_AUTHORING_PACKAGE_VERSION


@dataclass(frozen=True, slots=True)
class TeacherPersona:
    """Opaque teacher persona — no LLM prompt text."""

    persona_id: str = "default_tutor"
    tone: str = "supportive"
    extras: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StudentProfile:
    """Minimal student surface for authoring — no mastery/progression engines."""

    student_id: int = 0
    language_id: int = 0
    overall_cefr: str = ""
    locale: str = "en"
    extras: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LessonContext:
    """Lesson context for authoring — not a Runtime session."""

    lesson_id: str = ""
    step_id: str = "practice"
    context_hint: str = ""
    extras: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AuthoringContext:
    """Everything an authoring strategy may read.

    grammar_targets = WHAT to teach (sole authority).
    adaptive.learning_snapshot = HOW to teach (personalization only).
    """

    grammar_targets: tuple[str, ...]
    student_cefr: str
    learning_objective: str
    teacher_persona: TeacherPersona
    student_profile: StudentProfile
    lesson_context: LessonContext
    activity_type: str
    localization: str = "en"
    difficulty: ActivityDifficulty = ActivityDifficulty.guided
    adaptive: AdaptiveAuthoringContext = field(default_factory=AdaptiveAuthoringContext)
    versions: AuthoringVersionBundle = field(
        default_factory=lambda: AuthoringVersionBundle(
            catalog_version="1.0.0",
            grammar_schema_version=1,
            blueprint_version="1.0.0",
            activity_schema_version=1,
            planner_version="1.0.0",
        )
    )
    preferred_strategy_id: str = ""
    extras: dict[str, str] = field(default_factory=dict)

    @property
    def learning_snapshot(self) -> StudentLearningSnapshot:
        return self.adaptive.learning_snapshot


@dataclass(frozen=True, slots=True)
class AuthoringRequest:
    """Canonical authoring input — Grammar Targets are the sole learning truth."""

    context: AuthoringContext
    request_id: str = ""


@dataclass(frozen=True, slots=True)
class AuthoringResult:
    """Authoring envelope — content contract is specification only."""

    specification: ActivitySpecification
    strategy_id: str
    request_fingerprint: str = ""
    authoring_version: str = GRAMMAR_ACTIVITY_AUTHORING_PACKAGE_VERSION
    notes: str = ""


@runtime_checkable
class AuthoringStrategy(Protocol):
    """Strategy interface — Registry resolves by activity type."""

    @property
    def strategy_id(self) -> str: ...

    @property
    def supported_activity_types(self) -> frozenset[str]: ...

    def supports(self, activity_type: str) -> bool: ...

    def author(self, request: AuthoringRequest) -> ActivitySpecification:
        """Return ActivitySpecification only. No UI. (LLM authors live under llm/.)"""
        ...
