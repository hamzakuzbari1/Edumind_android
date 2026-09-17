"""Curriculum Engine V2 types — backend-owned educational intelligence for PackageConstraints."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ObjectiveKind(StrEnum):
    communicative = "communicative"
    vocabulary = "vocabulary"
    speaking = "speaking"
    transfer = "transfer"
    grammar = "grammar"  # reserved — Grammar module later


@dataclass(frozen=True, slots=True)
class VocabularyTarget:
    """Real lexical curriculum item Claude must teach (not invent)."""

    vocabulary_id: str
    lemma: str
    surface: str
    meaning: str
    communicative_purpose: str
    cefr_suitability: str
    expected_reuse: str
    example_usage: str
    required_lesson_frequency: int = 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "vocabulary_id": self.vocabulary_id,
            "lemma": self.lemma,
            "surface": self.surface,
            "meaning": self.meaning,
            "communicative_purpose": self.communicative_purpose,
            "cefr_suitability": self.cefr_suitability.upper(),
            "expected_reuse": self.expected_reuse,
            "example_usage": self.example_usage,
            "required_lesson_frequency": int(self.required_lesson_frequency),
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> VocabularyTarget:
        return VocabularyTarget(
            vocabulary_id=str(raw.get("vocabulary_id") or ""),
            lemma=str(raw.get("lemma") or raw.get("surface") or ""),
            surface=str(raw.get("surface") or ""),
            meaning=str(raw.get("meaning") or ""),
            communicative_purpose=str(raw.get("communicative_purpose") or ""),
            cefr_suitability=str(raw.get("cefr_suitability") or "A2").upper(),
            expected_reuse=str(raw.get("expected_reuse") or "story_teaching_discussion_practice"),
            example_usage=str(raw.get("example_usage") or ""),
            required_lesson_frequency=max(1, int(raw.get("required_lesson_frequency") or 2)),
        )


@dataclass(frozen=True, slots=True)
class EducationalObjective:
    """Typed educational objective — flattened into PackageConstraints.objectives for Claude."""

    kind: ObjectiveKind
    text: str
    priority: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "text": self.text,
            "priority": int(self.priority),
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> EducationalObjective:
        kind_raw = str(raw.get("kind") or "communicative")
        try:
            kind = ObjectiveKind(kind_raw)
        except ValueError:
            kind = ObjectiveKind.communicative
        return EducationalObjective(
            kind=kind,
            text=str(raw.get("text") or ""),
            priority=int(raw.get("priority") or 1),
        )


@dataclass(frozen=True, slots=True)
class GrammarTarget:
    """Curriculum-owned grammar topic Claude must demonstrate (not invent)."""

    grammar_topic_id: str
    label: str = ""
    cefr_suitability: str = ""
    focus_note: str = ""
    demonstration_forms: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "grammar_topic_id": self.grammar_topic_id,
            "label": self.label,
            "cefr_suitability": self.cefr_suitability,
            "focus_note": self.focus_note,
            "demonstration_forms": list(self.demonstration_forms),
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> GrammarTarget:
        forms = raw.get("demonstration_forms") or []
        return GrammarTarget(
            grammar_topic_id=str(raw.get("grammar_topic_id") or ""),
            label=str(raw.get("label") or ""),
            cefr_suitability=str(raw.get("cefr_suitability") or ""),
            focus_note=str(raw.get("focus_note") or ""),
            demonstration_forms=tuple(str(f) for f in forms if str(f).strip())
            if isinstance(forms, list)
            else (),
        )


@dataclass(frozen=True, slots=True)
class LessonAuthoringPolicy:
    """CEFR-differentiated density requirements Claude must satisfy.

    Story-first Speaking uses ``min_story_beats`` + word counts.
    ``min_dialogue_turns`` is retained as a dual-read alias during migration.
    """

    cefr: str
    min_story_beats: int
    min_input_word_count: int
    max_input_word_count: int
    target_vocabulary_count: int
    min_recycle_per_item: int
    teaching_block_min_chars: int
    reflection_prompt_count: int
    sentence_complexity: str
    question_depth: str
    reasoning_level: str
    transfer_expectation: str
    lesson_length_band: str
    difficulty: str
    include_guided_understanding_note: bool = True
    # Dual-read alias (M1–M2): same numeric guidance as min_story_beats for legacy caches
    min_dialogue_turns: int = 0

    def to_dict(self) -> dict[str, Any]:
        beats = self.min_story_beats or self.min_dialogue_turns or 6
        return {
            "cefr": self.cefr.upper(),
            "min_story_beats": beats,
            "min_dialogue_turns": beats,  # dual-read during transition
            "min_input_word_count": self.min_input_word_count,
            "max_input_word_count": self.max_input_word_count,
            "target_vocabulary_count": self.target_vocabulary_count,
            "min_recycle_per_item": self.min_recycle_per_item,
            "teaching_block_min_chars": self.teaching_block_min_chars,
            "reflection_prompt_count": self.reflection_prompt_count,
            "sentence_complexity": self.sentence_complexity,
            "question_depth": self.question_depth,
            "reasoning_level": self.reasoning_level,
            "transfer_expectation": self.transfer_expectation,
            "lesson_length_band": self.lesson_length_band,
            "difficulty": self.difficulty,
            "include_guided_understanding_note": self.include_guided_understanding_note,
            "required_sections": [
                "opening",
                "core_case",
                "vocabulary_discovery",
                "teaching_blocks",
                "guided_understanding",
                "communicative_discussion",
                "mini_practice",
                "reflection",
            ],
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> LessonAuthoringPolicy | None:
        if not isinstance(raw, dict):
            return None
        beats = int(
            raw.get("min_story_beats")
            or raw.get("min_dialogue_turns")
            or 6
        )
        min_words = int(raw.get("min_input_word_count") or 80)
        max_words = int(raw.get("max_input_word_count") or max(min_words + 80, 200))
        return LessonAuthoringPolicy(
            cefr=str(raw.get("cefr") or "A2").upper(),
            min_story_beats=beats,
            min_dialogue_turns=beats,
            min_input_word_count=min_words,
            max_input_word_count=max_words,
            target_vocabulary_count=int(raw.get("target_vocabulary_count") or 4),
            min_recycle_per_item=int(raw.get("min_recycle_per_item") or 2),
            teaching_block_min_chars=int(raw.get("teaching_block_min_chars") or 120),
            reflection_prompt_count=int(raw.get("reflection_prompt_count") or 2),
            sentence_complexity=str(raw.get("sentence_complexity") or "simple"),
            question_depth=str(raw.get("question_depth") or "literal_plus"),
            reasoning_level=str(raw.get("reasoning_level") or "basic"),
            transfer_expectation=str(raw.get("transfer_expectation") or "light"),
            lesson_length_band=str(raw.get("lesson_length_band") or "standard"),
            difficulty=str(raw.get("difficulty") or "standard"),
            include_guided_understanding_note=bool(
                raw.get("include_guided_understanding_note", True)
            ),
        )


@dataclass(frozen=True, slots=True)
class LexicalRecyclingPolicy:
    """Backend-owned reuse expectations across lesson sections."""

    min_appearances_per_item: int
    required_sections: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_appearances_per_item": self.min_appearances_per_item,
            "required_sections": list(self.required_sections),
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> LexicalRecyclingPolicy | None:
        if not isinstance(raw, dict):
            return None
        sections = raw.get("required_sections") or [
            "input_material",
            "teaching_blocks_authored",
            "discussion",
            "mini_practice",
        ]
        return LexicalRecyclingPolicy(
            min_appearances_per_item=max(1, int(raw.get("min_appearances_per_item") or 2)),
            required_sections=tuple(str(s) for s in sections),
        )


CURRICULUM_ENGINE_VERSION = "2.4.0"
