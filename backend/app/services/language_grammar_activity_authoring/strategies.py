"""Placeholder Authoring Strategies (V1.3) — no LLM / prompts."""

from __future__ import annotations

from app.services.language_grammar_activity_authoring.base import PlaceholderAuthoringStrategy
from app.services.language_grammar_activity_spec.enums import ActivityType


class SpeakingAuthoringStrategy(PlaceholderAuthoringStrategy):
    def __init__(self) -> None:
        super().__init__("speaking", frozenset({ActivityType.voice_recording.value}))


class WritingAuthoringStrategy(PlaceholderAuthoringStrategy):
    def __init__(self) -> None:
        super().__init__("writing", frozenset())


class ReadingAuthoringStrategy(PlaceholderAuthoringStrategy):
    def __init__(self) -> None:
        super().__init__("reading", frozenset())


class ListeningAuthoringStrategy(PlaceholderAuthoringStrategy):
    def __init__(self) -> None:
        super().__init__("listening", frozenset())


class GrammarExerciseAuthoringStrategy(PlaceholderAuthoringStrategy):
    def __init__(self) -> None:
        super().__init__("grammar_exercise", frozenset({ActivityType.free_text.value}))


class ConversationAuthoringStrategy(PlaceholderAuthoringStrategy):
    def __init__(self) -> None:
        super().__init__("conversation", frozenset({ActivityType.conversation.value}))


class MatchingAuthoringStrategy(PlaceholderAuthoringStrategy):
    def __init__(self) -> None:
        super().__init__("matching", frozenset({ActivityType.matching.value}))


class OrderingAuthoringStrategy(PlaceholderAuthoringStrategy):
    def __init__(self) -> None:
        super().__init__("ordering", frozenset({ActivityType.ordering.value}))


class FillBlankAuthoringStrategy(PlaceholderAuthoringStrategy):
    def __init__(self) -> None:
        super().__init__("fill_blank", frozenset({ActivityType.fill_in_the_blank.value}))


class MultipleChoiceAuthoringStrategy(PlaceholderAuthoringStrategy):
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


class SentenceBuilderAuthoringStrategy(PlaceholderAuthoringStrategy):
    def __init__(self) -> None:
        super().__init__(
            "sentence_builder",
            frozenset({ActivityType.sentence_building.value}),
        )


def builtin_authoring_strategies() -> tuple[PlaceholderAuthoringStrategy, ...]:
    return (
        SpeakingAuthoringStrategy(),
        WritingAuthoringStrategy(),
        ReadingAuthoringStrategy(),
        ListeningAuthoringStrategy(),
        GrammarExerciseAuthoringStrategy(),
        ConversationAuthoringStrategy(),
        MatchingAuthoringStrategy(),
        OrderingAuthoringStrategy(),
        FillBlankAuthoringStrategy(),
        MultipleChoiceAuthoringStrategy(),
        SentenceBuilderAuthoringStrategy(),
    )


DEFAULT_ACTIVITY_TYPE_TO_STRATEGY: dict[str, str] = {
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

REQUIRED_AUTHORING_STRATEGY_IDS: frozenset[str] = frozenset(
    {
        "speaking",
        "writing",
        "reading",
        "listening",
        "grammar_exercise",
        "conversation",
        "matching",
        "ordering",
        "fill_blank",
        "multiple_choice",
        "sentence_builder",
    }
)
