"""Executor contracts (G3.2) — placeholders; no Claude / skill engines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.language_grammar.enums import GrammarLessonStepKind
from app.services.language_grammar_activity_spec import ActivitySpecification
from app.services.language_grammar_lesson_planner.types import GrammarLessonBlueprint, GrammarLessonStep
from app.services.language_grammar_lesson_runtime.types import GrammarEvidenceRequest
from app.services.language_grammar_skill_executor import ExecutionResult


@dataclass(frozen=True, slots=True)
class StepExecutionResult:
    """Outcome of a single step dispatch — Runtime result (not content contract).

    Activity execution runs exclusively via Skill Executor Registry (V1.1).
    ``executor_id`` remains the Blueprint step-kind handoff id (backward compatible).
    ``skill_executor_id`` / ``execution_result`` carry Skill Execution Framework outcome.
    """

    success: bool
    evidence_request: GrammarEvidenceRequest | None = None
    notes: str = ""
    executor_id: str = ""
    # Canonical activity content (G3.35.1) — ActivitySpecification only.
    activity_specification: ActivitySpecification | None = None
    activity_id: str | None = None
    activity_provider_id: str | None = None
    # V1.1 Skill Execution Framework
    skill_executor_id: str | None = None
    execution_id: str | None = None
    execution_result: ExecutionResult | None = None
    execution_status: str | None = None


class StepExecutor(Protocol):
    """Dedicated executor for one or more step kinds."""

    executor_id: str

    def supports(self, kind: GrammarLessonStepKind) -> bool: ...

    def execute(
        self,
        *,
        step: GrammarLessonStep,
        blueprint: GrammarLessonBlueprint,
    ) -> StepExecutionResult: ...


class PlaceholderExecutor:
    """Deterministic no-op executor — never calls LLMs or skill runtimes."""

    def __init__(self, executor_id: str, kinds: frozenset[GrammarLessonStepKind]) -> None:
        self.executor_id = executor_id
        self._kinds = kinds

    def supports(self, kind: GrammarLessonStepKind) -> bool:
        return kind in self._kinds

    def execute(
        self,
        *,
        step: GrammarLessonStep,
        blueprint: GrammarLessonBlueprint,
    ) -> StepExecutionResult:
        evidence: GrammarEvidenceRequest | None = None
        if step.evidence_eligible:
            evidence = GrammarEvidenceRequest(
                step_id=step.step_id,
                grammar_id=blueprint.grammar_id,
                observation_types_hint=tuple(blueprint.evidence_plan.observation_types_hint)
                or ("formative",),
                context_hint=step.context_hint,
                skill=step.skill,
            )
        return StepExecutionResult(
            success=True,
            evidence_request=evidence,
            notes=f"placeholder:{self.executor_id}:{step.step_id}",
            executor_id=self.executor_id,
        )


class ExplanationExecutor(PlaceholderExecutor):
    def __init__(self) -> None:
        super().__init__("ExplanationExecutor", frozenset({GrammarLessonStepKind.explanation}))


class PracticeExecutor(PlaceholderExecutor):
    def __init__(self) -> None:
        super().__init__("PracticeExecutor", frozenset({GrammarLessonStepKind.practice}))


class WarmupExecutor(PlaceholderExecutor):
    def __init__(self) -> None:
        super().__init__("WarmupExecutor", frozenset({GrammarLessonStepKind.warmup}))


class QuickReviewExecutor(PlaceholderExecutor):
    def __init__(self) -> None:
        super().__init__("QuickReviewExecutor", frozenset({GrammarLessonStepKind.quick_review}))


class ReadingExecutor(PlaceholderExecutor):
    def __init__(self) -> None:
        super().__init__(
            "ReadingExecutor",
            frozenset({GrammarLessonStepKind.reading_reinforcement}),
        )


class ListeningExecutor(PlaceholderExecutor):
    def __init__(self) -> None:
        super().__init__(
            "ListeningExecutor",
            frozenset({GrammarLessonStepKind.listening_reinforcement}),
        )


class WritingExecutor(PlaceholderExecutor):
    def __init__(self) -> None:
        super().__init__(
            "WritingExecutor",
            frozenset({GrammarLessonStepKind.writing_reinforcement}),
        )


class SpeakingExecutor(PlaceholderExecutor):
    def __init__(self) -> None:
        super().__init__(
            "SpeakingExecutor",
            frozenset({GrammarLessonStepKind.speaking_reinforcement}),
        )


class ReinforcementExecutor(PlaceholderExecutor):
    """Generic G0 reinforcement kind — skill-agnostic placeholder."""

    def __init__(self) -> None:
        super().__init__(
            "ReinforcementExecutor",
            frozenset({GrammarLessonStepKind.reinforcement}),
        )


class ExitCheckExecutor(PlaceholderExecutor):
    def __init__(self) -> None:
        super().__init__("ExitCheckExecutor", frozenset({GrammarLessonStepKind.exit_check}))


class SummaryExecutor(PlaceholderExecutor):
    def __init__(self) -> None:
        super().__init__("SummaryExecutor", frozenset({GrammarLessonStepKind.summary}))


class HomeworkExecutor(PlaceholderExecutor):
    def __init__(self) -> None:
        super().__init__("HomeworkExecutor", frozenset({GrammarLessonStepKind.homework}))
