"""Deterministic Skill Executor lifecycle runner (G3.4)."""

from __future__ import annotations

from dataclasses import replace

from app.services.language_grammar_skill_executor.errors import (
    SkillExecutorDisabledError,
    SkillExecutorError,
)
from app.services.language_grammar_skill_executor.evidence_adapter import (
    adapt_execution_to_evidence,
    source_skill_for_executor,
)
from app.services.language_grammar_skill_executor.flags import skill_executor_enabled
from app.services.language_grammar_skill_executor.registry import (
    SkillExecutorRegistry,
    get_default_skill_executor_registry,
)
from app.services.language_grammar_skill_executor.resolution import resolve_executor
from app.services.language_grammar_skill_executor.tracking import (
    ExecutionIdGuard,
    get_default_execution_id_guard,
)
from app.services.language_grammar_skill_executor.types import (
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    LifecyclePhase,
    SkillExecutor,
)


def _sync_lifecycle_phases(executor: SkillExecutor, result: ExecutionResult) -> ExecutionResult:
    """Refresh result metadata after cleanup (phases tracked on placeholder base)."""
    phases = getattr(executor, "_phases", None)
    if not isinstance(phases, list):
        return result
    return replace(
        result,
        executor_metadata=replace(
            result.executor_metadata,
            lifecycle_phases_completed=tuple(phases),
        ),
    )


def run_lifecycle(
    executor: SkillExecutor,
    context: ExecutionContext,
    *,
    emit_evidence: bool = True,
    cancel: bool = False,
    cancel_reason: str = "",
) -> ExecutionResult:
    """Run the full deterministic lifecycle against one executor."""
    result: ExecutionResult | None = None
    try:
        executor.initialize(context)
        if cancel:
            result = executor.cancel(context, reason=cancel_reason)
        else:
            executor.prepare(context)
            executor.validate(context)
            result = executor.execute(context)
            result = executor.complete(context, result)
            if emit_evidence and result.status is ExecutionStatus.completed:
                evidence = adapt_execution_to_evidence(
                    result,
                    context=context,
                    source_skill=source_skill_for_executor(executor.executor_id),
                )
                result = replace(result, generated_evidence=evidence)
    finally:
        executor.cleanup(context)
    if result is None:
        raise SkillExecutorError("Lifecycle produced no ExecutionResult")
    return _sync_lifecycle_phases(executor, result)


def execute_activity(
    context: ExecutionContext,
    *,
    registry: SkillExecutorRegistry | None = None,
    preferred_executor_id: str | None = None,
    guard: ExecutionIdGuard | None = None,
    emit_evidence: bool = True,
    require_enabled: bool = True,
) -> ExecutionResult:
    """Resolve executor via Registry and run lifecycle — sole public execution entry."""
    if require_enabled:
        enabled = skill_executor_enabled() or (
            context.feature_flags.grammar_engine_enabled
            and context.feature_flags.skill_executor_enabled
        )
        if not enabled:
            raise SkillExecutorDisabledError(
                "Skill execution disabled (LANG_GRAMMAR_SKILL_EXECUTOR_ENABLED)"
            )

    eid_guard = guard or get_default_execution_id_guard()
    eid_guard.claim(context.execution_id)

    reg = registry or get_default_skill_executor_registry()
    executor = resolve_executor(
        context,
        registry=reg,
        preferred_executor_id=preferred_executor_id,
    )
    if not isinstance(executor, SkillExecutor):
        raise SkillExecutorError("Resolved object is not a SkillExecutor")

    return run_lifecycle(executor, context, emit_evidence=emit_evidence)


def lifecycle_methods_present(executor: SkillExecutor) -> tuple[str, ...]:
    """Return lifecycle method names present on the executor (for audits)."""
    present: list[str] = []
    for phase in LifecyclePhase:
        if callable(getattr(executor, phase.value, None)):
            present.append(phase.value)
    return tuple(present)
