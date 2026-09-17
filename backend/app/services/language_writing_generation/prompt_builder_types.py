"""Prompt Builder types (W4) — structured LLM prompts from blueprint only."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

PROMPT_BUILDER_VERSION = "4.0.0"


class PromptSectionKey(StrEnum):
    """Canonical prompt sections — LLM receives these only via Prompt Builder."""

    system = "system"
    role = "role"
    mission = "mission"
    grammar = "grammar"
    vocabulary = "vocabulary"
    output_format = "output_format"
    constraints = "constraints"
    success_criteria = "success_criteria"
    rules = "rules"


@dataclass(frozen=True, slots=True)
class WritingPromptSection:
    key: PromptSectionKey
    content: str


@dataclass(frozen=True, slots=True)
class WritingPromptBundle:
    """Structured prompt for future LLM — blueprint-derived only; not student-facing."""

    sections: tuple[WritingPromptSection, ...]
    blueprint_id: str
    blueprint_version: str
    blueprint_hash: str
    builder_version: str = PROMPT_BUILDER_VERSION

    def section(self, key: PromptSectionKey) -> str:
        for s in self.sections:
            if s.key == key:
                return s.content
        return ""

    def to_prompt_dict(self) -> dict[str, str]:
        return {s.key.value: s.content for s in self.sections}

    @property
    def required_section_keys(self) -> tuple[PromptSectionKey, ...]:
        return tuple(PromptSectionKey)


PROMPT_FORBIDDEN_CONTEXT_SOURCES: frozenset[str] = frozenset(
    {
        "student",
        "student_id",
        "database",
        "progression",
        "topic_universe",
        "knowledge_chain",
        "goal_profile",
        "grammar_progression",
        "vocabulary_progression",
        "LessonPlannerInput",
    }
)

LLM_FORBIDDEN_DIRECT_ACCESS: frozenset[str] = frozenset(
    {
        "student",
        "database",
        "progression",
        "topic_universe",
        "knowledge_chain",
        "WritingLessonBlueprint",
        "LessonPlannerInput",
    }
)
