"""Types for Writing Generation metadata (W0)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing.enums import (
    ContextComplexity,
    OfficialWritingCEFR,
    WritingArc,
    WritingGoal,
    WritingTopicId,
)
from app.services.language_writing_generation import (
    WRITING_CHALLENGE_KEY,
    WRITING_COACH_KEY,
    WRITING_CURRICULUM_KEY,
    WRITING_GENERATION_KEY,
    WRITING_GOAL_KEY,
)


@dataclass(frozen=True, slots=True)
class WritingGenerationSpec:
    """Inputs required to generate a writing lesson (contract only — W0)."""

    official_cefr: OfficialWritingCEFR
    arc_stage: WritingArc
    topic_id: WritingTopicId
    chain_id: str
    chain_node_id: str
    context_complexity: ContextComplexity
    goal: WritingGoal
    task_type: str
    genre: str
    min_words: int
    max_words: int
    time_limit_minutes: int | None = None
    vocabulary_seeds: tuple[str, ...] = ()
    grammar_focus: str = ""


@dataclass(frozen=True, slots=True)
class WritingGenerationMetadata:
    """Stored under body_json[writing_generation] after generation."""

    spec_version: str
    generator_version: str
    chain_id: str
    chain_node_id: str
    validated: bool = False
    validation_notes: tuple[str, ...] = ()


def writing_body_json_keys() -> frozenset[str]:
    """Required top-level metadata keys on generated writing content."""
    return frozenset(
        {
            WRITING_CURRICULUM_KEY,
            WRITING_GOAL_KEY,
            WRITING_GENERATION_KEY,
        }
    )


@dataclass(frozen=True, slots=True)
class WritingCurriculumMetadata:
    """Stored under body_json[writing_curriculum]."""

    official_cefr: str
    arc_stage: str
    topic_id: str
    chain_id: str
    chain_node_id: str
    chain_position: int
    context_complexity: int

    def to_dict(self) -> dict[str, object]:
        return {
            "official_cefr": self.official_cefr,
            "arc_stage": self.arc_stage,
            "topic_id": self.topic_id,
            "chain_id": self.chain_id,
            "chain_node_id": self.chain_node_id,
            "chain_position": self.chain_position,
            "context_complexity": self.context_complexity,
        }
