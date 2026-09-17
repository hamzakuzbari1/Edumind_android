"""Placeholder Skill Executor plugins (G3.4) — lifecycle only, no real skill logic."""

from __future__ import annotations

from app.services.language_grammar_activity_spec.enums import ActivityType
from app.services.language_grammar_skill_executor.base import PlaceholderSkillExecutor


class SpeakingExecutor(PlaceholderSkillExecutor):
    def __init__(self) -> None:
        super().__init__(
            "speaking",
            frozenset({ActivityType.voice_recording.value}),
        )


class ReadingExecutor(PlaceholderSkillExecutor):
    """Skill-named placeholder — resolvable by executor_id; types via registry aliases later."""

    def __init__(self) -> None:
        super().__init__("reading", frozenset())


class ListeningExecutor(PlaceholderSkillExecutor):
    def __init__(self) -> None:
        super().__init__("listening", frozenset())


class WritingExecutor(PlaceholderSkillExecutor):
    def __init__(self) -> None:
        super().__init__("writing", frozenset())


class GrammarExerciseExecutor(PlaceholderSkillExecutor):
    def __init__(self) -> None:
        super().__init__(
            "grammar_exercise",
            frozenset({ActivityType.free_text.value}),
        )


class ConversationExecutor(PlaceholderSkillExecutor):
    def __init__(self) -> None:
        super().__init__(
            "conversation",
            frozenset({ActivityType.conversation.value}),
        )


class OrderingExecutor(PlaceholderSkillExecutor):
    def __init__(self) -> None:
        super().__init__(
            "ordering",
            frozenset({ActivityType.ordering.value}),
        )


class MatchingExecutor(PlaceholderSkillExecutor):
    def __init__(self) -> None:
        super().__init__(
            "matching",
            frozenset({ActivityType.matching.value}),
        )


class FillBlankExecutor(PlaceholderSkillExecutor):
    def __init__(self) -> None:
        super().__init__(
            "fill_blank",
            frozenset({ActivityType.fill_in_the_blank.value}),
        )


class MultipleChoiceExecutor(PlaceholderSkillExecutor):
    def __init__(self) -> None:
        super().__init__(
            "multiple_choice",
            frozenset(
                {
                    ActivityType.multiple_choice.value,
                    ActivityType.selection.value,
                }
            ),
        )


class SentenceBuilderExecutor(PlaceholderSkillExecutor):
    def __init__(self) -> None:
        super().__init__(
            "sentence_builder",
            frozenset({ActivityType.sentence_building.value}),
        )


def builtin_placeholder_executors() -> tuple[PlaceholderSkillExecutor, ...]:
    """Deterministic builtin plugin set — order does not affect resolution by id."""
    return (
        SpeakingExecutor(),
        ReadingExecutor(),
        ListeningExecutor(),
        WritingExecutor(),
        GrammarExerciseExecutor(),
        ConversationExecutor(),
        OrderingExecutor(),
        MatchingExecutor(),
        FillBlankExecutor(),
        MultipleChoiceExecutor(),
        SentenceBuilderExecutor(),
    )


# Canonical activity_type → preferred executor_id (Registry resolves; Runtime never branches).
DEFAULT_ACTIVITY_TYPE_TO_EXECUTOR: dict[str, str] = {
    ActivityType.free_text.value: "grammar_exercise",
    ActivityType.multiple_choice.value: "multiple_choice",
    ActivityType.voice_recording.value: "speaking",
    ActivityType.ordering.value: "ordering",
    ActivityType.matching.value: "matching",
    ActivityType.fill_in_the_blank.value: "fill_blank",
    ActivityType.selection.value: "multiple_choice",
    ActivityType.conversation.value: "conversation",
    ActivityType.sentence_building.value: "sentence_builder",
}

REQUIRED_PLACEHOLDER_EXECUTOR_IDS: frozenset[str] = frozenset(
    {
        "speaking",
        "reading",
        "listening",
        "writing",
        "grammar_exercise",
        "conversation",
        "ordering",
        "matching",
        "fill_blank",
        "multiple_choice",
        "sentence_builder",
    }
)
