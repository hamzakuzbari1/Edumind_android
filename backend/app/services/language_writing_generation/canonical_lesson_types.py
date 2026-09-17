"""Canonical Generated Lesson types (W5) — final output after normalize/validate/repair."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing_generation.mission_builder_types import WritingEstimatedTime
from app.services.language_writing_generation.normalizer_types import WritingNormalizedLessonDraft

CANONICAL_LESSON_SCHEMA_VERSION = "5.0.0"


@dataclass(frozen=True, slots=True)
class WritingCanonicalGeneratedLesson:
    """Canonical lesson after generation pipeline — ready for persistence and student experience."""

    mission_title: str
    writing_context: str
    instructions: tuple[str, ...]
    writing_prompt: str
    constraints: tuple[str, ...]
    checklist: tuple[str, ...]
    tips: tuple[str, ...]
    learning_outcomes: tuple[str, ...]
    success_criteria: tuple[str, ...]
    expected_output: str
    grammar_display: str
    vocabulary_display: str
    estimated_time: WritingEstimatedTime
    blueprint_id: str
    blueprint_version: str
    blueprint_schema_version: str
    blueprint_hash: str
    generation_hash: str
    canonical_schema_version: str = CANONICAL_LESSON_SCHEMA_VERSION

    @staticmethod
    def from_repaired_draft(
        draft: WritingNormalizedLessonDraft,
        *,
        blueprint_id: str,
        blueprint_version: str,
        blueprint_schema_version: str,
        blueprint_hash: str,
        generation_hash: str,
        writing_minutes: int,
        revision_minutes: int,
        total_minutes: int,
    ) -> WritingCanonicalGeneratedLesson:
        return WritingCanonicalGeneratedLesson(
            mission_title=draft.mission_title,
            writing_context=draft.writing_context,
            instructions=draft.instructions,
            writing_prompt=draft.writing_prompt,
            constraints=draft.constraints,
            checklist=draft.checklist,
            tips=draft.tips,
            learning_outcomes=draft.learning_outcomes,
            success_criteria=draft.success_criteria,
            expected_output=draft.expected_output,
            grammar_display=draft.grammar_display,
            vocabulary_display=draft.vocabulary_display,
            estimated_time=WritingEstimatedTime(
                writing_minutes=writing_minutes,
                revision_minutes=revision_minutes,
                total_minutes=total_minutes,
            ),
            blueprint_id=blueprint_id,
            blueprint_version=blueprint_version,
            blueprint_schema_version=blueprint_schema_version,
            blueprint_hash=blueprint_hash,
            generation_hash=generation_hash,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "mission_title": self.mission_title,
            "writing_context": self.writing_context,
            "instructions": list(self.instructions),
            "writing_prompt": self.writing_prompt,
            "constraints": list(self.constraints),
            "checklist": list(self.checklist),
            "tips": list(self.tips),
            "learning_outcomes": list(self.learning_outcomes),
            "success_criteria": list(self.success_criteria),
            "expected_output": self.expected_output,
            "grammar_display": self.grammar_display,
            "vocabulary_display": self.vocabulary_display,
            "estimated_time": {
                "writing_minutes": self.estimated_time.writing_minutes,
                "revision_minutes": self.estimated_time.revision_minutes,
                "total_minutes": self.estimated_time.total_minutes,
            },
            "blueprint_id": self.blueprint_id,
            "blueprint_version": self.blueprint_version,
            "blueprint_schema_version": self.blueprint_schema_version,
            "blueprint_hash": self.blueprint_hash,
            "generation_hash": self.generation_hash,
            "canonical_schema_version": self.canonical_schema_version,
        }


def canonical_lesson_fields_complete(lesson: WritingCanonicalGeneratedLesson) -> bool:
    return bool(
        lesson.mission_title.strip()
        and lesson.writing_context.strip()
        and lesson.instructions
        and lesson.writing_prompt.strip()
        and lesson.checklist
        and lesson.learning_outcomes
        and lesson.success_criteria
        and lesson.expected_output
        and lesson.grammar_display
        and lesson.vocabulary_display
        and lesson.estimated_time.total_minutes > 0
        and lesson.blueprint_hash
        and lesson.generation_hash
    )
