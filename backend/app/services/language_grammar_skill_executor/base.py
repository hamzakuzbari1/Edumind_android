"""Placeholder Skill Executor base — lifecycle only, no business logic (G3.4)."""

from __future__ import annotations

from dataclasses import replace

from app.services.language_grammar_activity_spec import (
    ActivitySpecError,
    validate_activity_specification,
)
from app.services.language_grammar_skill_executor.errors import (
    BrokenSpecificationError,
    SkillExecutorError,
)
from app.services.language_grammar_skill_executor.types import (
    CollectedOutput,
    CompletionState,
    ExecutionArtifact,
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTiming,
    ExecutorMetadata,
    LifecyclePhase,
)


class PlaceholderSkillExecutor:
    """Deterministic no-op skill executor — never calls LLMs or skill engines."""

    executor_version: str = "1.0.0"

    def __init__(
        self,
        executor_id: str,
        supported_activity_types: frozenset[str],
    ) -> None:
        self._executor_id = executor_id
        self._supported_activity_types = frozenset(supported_activity_types)
        self._phases: list[str] = []

    @property
    def executor_id(self) -> str:
        return self._executor_id

    @property
    def supported_activity_types(self) -> frozenset[str]:
        return self._supported_activity_types

    def supports(self, activity_type: str) -> bool:
        return activity_type in self._supported_activity_types

    def initialize(self, context: ExecutionContext) -> None:
        self._phases = [LifecyclePhase.initialize.value]
        if not context.execution_id.strip():
            raise SkillExecutorError("Missing execution_id")
        if context.specification is None:
            raise SkillExecutorError("Missing ActivitySpecification")

    def prepare(self, context: ExecutionContext) -> None:
        self._phases.append(LifecyclePhase.prepare.value)
        _ = context  # context available for future real executors

    def validate(self, context: ExecutionContext) -> None:
        self._phases.append(LifecyclePhase.validate.value)
        spec = context.specification
        if not spec.completion_rules:
            raise BrokenSpecificationError("Missing completion_rules")
        try:
            validate_activity_specification(spec)
        except ActivitySpecError as exc:
            raise BrokenSpecificationError(str(exc)) from exc

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        self._phases.append(LifecyclePhase.execute.value)
        spec = context.specification
        outputs = tuple(
            CollectedOutput(
                output_id=out.output_id,
                output_type=out.output_type,
                value="",
                present=False,
            )
            for out in spec.expected_outputs
        )
        return ExecutionResult(
            execution_id=context.execution_id,
            status=ExecutionStatus.running,
            completion_state=CompletionState.incomplete,
            artifacts=(
                ExecutionArtifact(
                    artifact_id=f"art_{context.execution_id}",
                    kind="placeholder",
                    metadata={"activity_type": spec.activity_type},
                ),
            ),
            collected_outputs=outputs,
            generated_evidence=(),
            warnings=("placeholder_executor:no_business_logic",),
            timing=ExecutionTiming(
                started_at=context.metadata.as_of,
                finished_at="",
                duration_ms=0,
            ),
            executor_metadata=ExecutorMetadata(
                executor_id=self.executor_id,
                executor_version=self.executor_version,
                lifecycle_phases_completed=tuple(self._phases),
            ),
            notes=f"placeholder:{self.executor_id}:{spec.activity_type}",
        )

    def complete(self, context: ExecutionContext, result: ExecutionResult) -> ExecutionResult:
        self._phases.append(LifecyclePhase.complete.value)
        return replace(
            result,
            status=ExecutionStatus.completed,
            completion_state=CompletionState.complete,
            timing=replace(
                result.timing,
                finished_at=context.metadata.as_of or result.timing.started_at,
                duration_ms=0,
            ),
            executor_metadata=replace(
                result.executor_metadata,
                lifecycle_phases_completed=tuple(self._phases),
            ),
        )

    def cancel(self, context: ExecutionContext, reason: str = "") -> ExecutionResult:
        self._phases.append(LifecyclePhase.cancel.value)
        return ExecutionResult(
            execution_id=context.execution_id,
            status=ExecutionStatus.cancelled,
            completion_state=CompletionState.incomplete,
            warnings=(reason or "cancelled",),
            timing=ExecutionTiming(
                started_at=context.metadata.as_of,
                finished_at=context.metadata.as_of,
            ),
            executor_metadata=ExecutorMetadata(
                executor_id=self.executor_id,
                executor_version=self.executor_version,
                lifecycle_phases_completed=tuple(self._phases),
            ),
            notes=f"cancelled:{self.executor_id}",
        )

    def cleanup(self, context: ExecutionContext) -> None:
        self._phases.append(LifecyclePhase.cleanup.value)
        _ = context
