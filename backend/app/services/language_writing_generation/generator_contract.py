"""Writing Generator contracts (W3.1 FROZEN) — transforms Blueprint into presentation only."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing_lesson_planner.types import (
    GENERATOR_FORBIDDEN_CONTEXT_SOURCES,
    WritingLessonBlueprint,
)

GENERATOR_SCHEMA_VERSION = "3.1.0"

# Packages the generator must never import (verified in W3 script).
GENERATOR_FORBIDDEN_IMPORT_PACKAGES: frozenset[str] = frozenset(
    {
        "language_writing_curriculum",
        "language_writing_topic_universe",
        "language_writing_knowledge_chain",
        "language_writing_grammar_progression",
        "language_writing_lexis_progression",
        "language_writing_progression",
        "language_writing_coach",
        "language_writing_evaluator",
        "language_writing_explainability",
        "language_writing_revision",
    }
)


@dataclass(frozen=True, slots=True)
class WritingGeneratorInput:
    """Generator receives blueprint only — no educational context beyond blueprint."""

    blueprint: WritingLessonBlueprint
    generator_version: str = GENERATOR_SCHEMA_VERSION
    locale: str = "en"


@dataclass(frozen=True, slots=True)
class WritingMissionAssembly:
    """Presentation-layer mission — no educational decisions."""

    mission_title: str
    mission_summary: str
    instructions: tuple[str, ...]
    writing_prompt: str
    constraints: tuple[str, ...]
    expected_output_label: str
    student_context: str
    checklist: tuple[str, ...] = ()
    scaffold_outline: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WritingGeneratedLesson:
    """Output of Writing Generator — presentation + blueprint version echo."""

    assembly: WritingMissionAssembly
    blueprint_id: str
    blueprint_version: str
    blueprint_schema_version: str
    blueprint_hash: str
    generator_version: str
    learning_outcomes: tuple[str, ...]
    success_criteria_labels: tuple[str, ...]
    grammar_primary: str
    vocabulary_primary: tuple[str, ...]
    expected_writing_output: str
    personal_goal: str

    def to_presentation_dict(self) -> dict[str, object]:
        return {
            "mission_title": self.assembly.mission_title,
            "mission_summary": self.assembly.mission_summary,
            "instructions": list(self.assembly.instructions),
            "writing_prompt": self.assembly.writing_prompt,
            "constraints": list(self.assembly.constraints),
            "expected_output_label": self.assembly.expected_output_label,
            "student_context": self.assembly.student_context,
            "checklist": list(self.assembly.checklist),
            "scaffold_outline": list(self.assembly.scaffold_outline),
            "blueprint_version": self.blueprint_version,
            "blueprint_schema_version": self.blueprint_schema_version,
            "blueprint_hash": self.blueprint_hash,
        }


GENERATOR_ALLOWED_INPUT_TYPES: frozenset[str] = frozenset({"WritingGeneratorInput", "WritingLessonBlueprint"})

GENERATOR_ALLOWED_INPUT_FIELDS: frozenset[str] = frozenset({"blueprint", "generator_version", "locale"})

__all__ = [
    "GENERATOR_ALLOWED_INPUT_FIELDS",
    "GENERATOR_ALLOWED_INPUT_TYPES",
    "GENERATOR_FORBIDDEN_CONTEXT_SOURCES",
    "GENERATOR_FORBIDDEN_IMPORT_PACKAGES",
    "GENERATOR_SCHEMA_VERSION",
    "WritingGeneratedLesson",
    "WritingGeneratorInput",
    "WritingLessonBlueprint",
    "WritingMissionAssembly",
]
