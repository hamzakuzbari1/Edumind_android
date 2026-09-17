"""Executor registry — maps step kinds to dedicated executors."""

from __future__ import annotations

from app.services.language_grammar.enums import GrammarLessonStepKind
from app.services.language_grammar_lesson_runtime.executors.base import (
    ExitCheckExecutor,
    ExplanationExecutor,
    HomeworkExecutor,
    ListeningExecutor,
    PlaceholderExecutor,
    PracticeExecutor,
    QuickReviewExecutor,
    ReadingExecutor,
    ReinforcementExecutor,
    SpeakingExecutor,
    StepExecutor,
    SummaryExecutor,
    WarmupExecutor,
    WritingExecutor,
)


class GrammarExecutorRegistry:
    """Immutable registry of step executors. No planner / mastery / Claude deps."""

    def __init__(self, executors: tuple[StepExecutor, ...] | None = None) -> None:
        self._executors: tuple[StepExecutor, ...] = executors or default_executors()
        by_kind: dict[GrammarLessonStepKind, StepExecutor] = {}
        for ex in self._executors:
            for kind in GrammarLessonStepKind:
                if ex.supports(kind):
                    if kind in by_kind:
                        raise ValueError(f"Duplicate executor for kind {kind}")
                    by_kind[kind] = ex
        self._by_kind = by_kind

    def resolve(self, kind: GrammarLessonStepKind) -> StepExecutor:
        ex = self._by_kind.get(kind)
        if ex is None:
            raise KeyError(f"No executor registered for step kind: {kind}")
        return ex

    def executor_ids(self) -> tuple[str, ...]:
        return tuple(ex.executor_id for ex in self._executors)


def default_executors() -> tuple[StepExecutor, ...]:
    return (
        WarmupExecutor(),
        QuickReviewExecutor(),
        ExplanationExecutor(),
        PracticeExecutor(),
        ReadingExecutor(),
        ListeningExecutor(),
        WritingExecutor(),
        SpeakingExecutor(),
        ReinforcementExecutor(),
        ExitCheckExecutor(),
        SummaryExecutor(),
        HomeworkExecutor(),
    )


_DEFAULT_REGISTRY = GrammarExecutorRegistry()


def get_default_registry() -> GrammarExecutorRegistry:
    return _DEFAULT_REGISTRY
