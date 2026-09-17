"""Runtime → Skill Executor Registry bridge (V1.1).

Runtime discovers executors only via SkillExecutorRegistry.
No activity-type if-branches. No Provider / Claude / skill-engine leakage.
"""

from __future__ import annotations

import time
from dataclasses import replace
from uuid import uuid4

from app.services.language_grammar_activity_spec import ActivitySpecification
from app.services.language_grammar_skill_executor import (
    BrokenSpecificationError,
    DuplicateExecutionIdError,
    ExecutionContext,
    ExecutionFeatureFlags,
    ExecutionIdGuard,
    ExecutionMetadata,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTiming,
    MissingExecutorError,
    SkillExecutorDisabledError,
    SkillExecutorError,
    SkillExecutorRegistry,
    StudentContext,
    get_default_execution_id_guard,
    get_default_skill_executor_registry,
    resolve_executor,
    run_lifecycle,
)
from app.services.language_grammar_skill_executor.flags import skill_executor_strict


class SkillExecutionBridgeError(ValueError):
    """Structured Runtime-facing skill execution failure."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def build_execution_id(
    *,
    lesson_id: str,
    step_id: str,
    step_index: int,
    as_of: str = "",
) -> str:
    """Unique id per step attempt (tracking only — no analytics)."""
    stamp = as_of or uuid4().hex[:12]
    return f"{lesson_id}:{step_id}:{step_index}:{stamp}"


def build_execution_context(
    specification: ActivitySpecification,
    *,
    student_id: int,
    language_id: int,
    lesson_id: str,
    blueprint_id: str,
    execution_id: str,
    overall_cefr: str = "",
    locale: str = "en",
    as_of: str = "",
    attempt_index: int = 0,
    preferred_executor_id: str = "",
) -> ExecutionContext:
    """Build canonical Skill Executor input — no Runtime session objects."""
    return ExecutionContext(
        specification=specification,
        student=StudentContext(
            student_id=student_id,
            language_id=language_id,
            overall_cefr=overall_cefr,
            locale=locale,
        ),
        runtime_session_id=lesson_id,
        blueprint_id=blueprint_id,
        execution_id=execution_id,
        localization=locale or specification.localization_default_locale,
        feature_flags=ExecutionFeatureFlags(
            grammar_engine_enabled=True,
            skill_executor_enabled=True,
            skill_executor_strict=skill_executor_strict(),
        ),
        metadata=ExecutionMetadata(
            as_of=as_of,
            attempt_index=attempt_index,
            preferred_executor_id=preferred_executor_id,
            extras={
                "step_id": specification.step_id,
                "activity_type": specification.activity_type,
            },
        ),
    )


def run_skill_execution(
    specification: ActivitySpecification,
    *,
    student_id: int,
    language_id: int,
    lesson_id: str,
    blueprint_fingerprint: str,
    step_index: int,
    overall_cefr: str = "",
    locale: str = "en",
    as_of: str = "",
    attempt_index: int = 0,
    preferred_executor_id: str | None = None,
    skill_registry: SkillExecutorRegistry | None = None,
    guard: ExecutionIdGuard | None = None,
    cancel: bool = False,
    cancel_reason: str = "",
) -> ExecutionResult:
    """Resolve via Registry and run lifecycle. Structured errors only."""
    execution_id = build_execution_id(
        lesson_id=lesson_id,
        step_id=specification.step_id,
        step_index=step_index,
        as_of=as_of,
    )
    context = build_execution_context(
        specification,
        student_id=student_id,
        language_id=language_id,
        lesson_id=lesson_id,
        blueprint_id=blueprint_fingerprint,
        execution_id=execution_id,
        overall_cefr=overall_cefr,
        locale=locale,
        as_of=as_of,
        attempt_index=attempt_index,
        preferred_executor_id=preferred_executor_id or "",
    )

    reg = skill_registry or get_default_skill_executor_registry()
    eid_guard = guard or get_default_execution_id_guard()
    started = time.perf_counter()

    try:
        eid_guard.claim(context.execution_id)
        if cancel:
            executor = resolve_executor(
                context,
                registry=reg,
                preferred_executor_id=preferred_executor_id,
            )
            result = run_lifecycle(
                executor,
                context,
                emit_evidence=False,
                cancel=True,
                cancel_reason=cancel_reason or "cancelled",
            )
        else:
            executor = resolve_executor(
                context,
                registry=reg,
                preferred_executor_id=preferred_executor_id,
            )
            result = run_lifecycle(executor, context, emit_evidence=True)
    except SkillExecutionBridgeError:
        raise
    except MissingExecutorError as exc:
        raise SkillExecutionBridgeError("missing_executor", str(exc)) from exc
    except BrokenSpecificationError as exc:
        raise SkillExecutionBridgeError("validation_failure", str(exc)) from exc
    except DuplicateExecutionIdError as exc:
        raise SkillExecutionBridgeError("duplicate_execution_id", str(exc)) from exc
    except SkillExecutorDisabledError as exc:
        raise SkillExecutionBridgeError("executor_disabled", str(exc)) from exc
    except SkillExecutorError as exc:
        code = "unknown_activity_type" if "Unknown activity type" in str(exc) else "execution_failure"
        raise SkillExecutionBridgeError(code, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise SkillExecutionBridgeError("lifecycle_interruption", str(exc)) from exc

    if result.status is ExecutionStatus.failed:
        raise SkillExecutionBridgeError(
            "execution_failure",
            result.notes or f"Skill executor failed: {result.executor_metadata.executor_id}",
        )

    elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
    if result.timing.duration_ms == 0:
        result = replace(
            result,
            timing=ExecutionTiming(
                started_at=result.timing.started_at or as_of,
                finished_at=result.timing.finished_at or as_of,
                duration_ms=elapsed_ms,
            ),
        )
    return result
