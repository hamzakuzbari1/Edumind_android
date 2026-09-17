"""Learning Path & Explainability Engine (Phase 3.4 / 2.1) — read-only."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.language_listening_explainability.builder import EXPECTED_SIGNALS, build_lesson_explainability
    from app.services.language_listening_explainability.engine import generate_listening_explainability
    from app.services.language_listening_explainability.facts import (
        ExplainabilityFacts,
        build_explainability_facts,
        build_explainability_facts_from_body,
    )
    from app.services.language_listening_explainability.learning_path import build_learning_path
    from app.services.language_listening_explainability.signals import extract_signals
    from app.services.language_listening_explainability.student_summary import build_student_summary
    from app.services.language_listening_explainability.teacher_summary import build_teacher_summary
    from app.services.language_listening_explainability.types import (
        ExplainabilityResult,
        ExplainabilitySignals,
        ExplainabilityTelemetry,
        LearningPath,
        LearningPathObjective,
        LessonExplainability,
        ObjectivePathStatus,
        StudentSummary,
        TeacherSummary,
    )

__all__ = (
    "EXPECTED_SIGNALS",
    "ExplainabilityFacts",
    "ExplainabilityResult",
    "ExplainabilitySignals",
    "ExplainabilityTelemetry",
    "LearningPath",
    "LearningPathObjective",
    "LessonExplainability",
    "ObjectivePathStatus",
    "StudentSummary",
    "TeacherSummary",
    "build_explainability_facts",
    "build_explainability_facts_from_body",
    "build_learning_path",
    "build_lesson_explainability",
    "build_student_summary",
    "build_teacher_summary",
    "extract_signals",
    "generate_listening_explainability",
)

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "EXPECTED_SIGNALS": ("app.services.language_listening_explainability.builder", "EXPECTED_SIGNALS"),
    "ExplainabilityFacts": ("app.services.language_listening_explainability.facts", "ExplainabilityFacts"),
    "ExplainabilityResult": ("app.services.language_listening_explainability.types", "ExplainabilityResult"),
    "ExplainabilitySignals": ("app.services.language_listening_explainability.types", "ExplainabilitySignals"),
    "ExplainabilityTelemetry": ("app.services.language_listening_explainability.types", "ExplainabilityTelemetry"),
    "LearningPath": ("app.services.language_listening_explainability.types", "LearningPath"),
    "LearningPathObjective": ("app.services.language_listening_explainability.types", "LearningPathObjective"),
    "LessonExplainability": ("app.services.language_listening_explainability.types", "LessonExplainability"),
    "ObjectivePathStatus": ("app.services.language_listening_explainability.types", "ObjectivePathStatus"),
    "StudentSummary": ("app.services.language_listening_explainability.types", "StudentSummary"),
    "TeacherSummary": ("app.services.language_listening_explainability.types", "TeacherSummary"),
    "build_explainability_facts": (
        "app.services.language_listening_explainability.facts",
        "build_explainability_facts",
    ),
    "build_explainability_facts_from_body": (
        "app.services.language_listening_explainability.facts",
        "build_explainability_facts_from_body",
    ),
    "build_learning_path": ("app.services.language_listening_explainability.learning_path", "build_learning_path"),
    "build_lesson_explainability": (
        "app.services.language_listening_explainability.builder",
        "build_lesson_explainability",
    ),
    "build_student_summary": (
        "app.services.language_listening_explainability.student_summary",
        "build_student_summary",
    ),
    "build_teacher_summary": (
        "app.services.language_listening_explainability.teacher_summary",
        "build_teacher_summary",
    ),
    "extract_signals": ("app.services.language_listening_explainability.signals", "extract_signals"),
    "generate_listening_explainability": (
        "app.services.language_listening_explainability.engine",
        "generate_listening_explainability",
    ),
}


def __getattr__(name: str):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    import importlib

    module = importlib.import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
