"""Step dispatcher — Provider Spec + Skill Executor Registry (V1.1)."""

from __future__ import annotations

from app.services.language_grammar_activity_provider import (
    ActivityExecutionContext,
    GrammarActivityProviderId,
    GrammarActivityProviderRegistry,
    GrammarRuntimeContext,
    GrammarStudentContext,
    provide_activity,
)
from app.services.language_grammar_activity_spec import ActivitySpecification
from app.services.language_grammar_lesson_planner.types import GrammarLessonBlueprint, GrammarLessonStep
from app.services.language_grammar_lesson_runtime.executors.base import StepExecutionResult
from app.services.language_grammar_lesson_runtime.executors.registry import (
    GrammarExecutorRegistry,
    get_default_registry,
)
from app.services.language_grammar_lesson_runtime.skill_execution_bridge import (
    SkillExecutionBridgeError,
    run_skill_execution,
)
from app.services.language_grammar_lesson_runtime.types import GrammarEvidenceRequest
from app.services.language_grammar_skill_executor import (
    ExecutionIdGuard,
    ExecutionStatus,
    SkillExecutorRegistry,
)


class GrammarRuntimeError(ValueError):
    """Invalid runtime transition or blueprint execution error."""


def _compat_evidence_request(
    step: GrammarLessonStep,
    blueprint: GrammarLessonBlueprint,
) -> GrammarEvidenceRequest | None:
    """Preserve G3.2 evidence_request surface when step is evidence-eligible."""
    if not step.evidence_eligible:
        return None
    return GrammarEvidenceRequest(
        step_id=step.step_id,
        grammar_id=blueprint.grammar_id,
        observation_types_hint=tuple(blueprint.evidence_plan.observation_types_hint) or ("formative",),
        context_hint=step.context_hint,
        skill=step.skill,
    )


def dispatch_step(
    step: GrammarLessonStep,
    blueprint: GrammarLessonBlueprint,
    *,
    registry: GrammarExecutorRegistry | None = None,
    student_id: int = 0,
    language_id: int = 0,
    lesson_id: str = "",
    step_index: int = 0,
    completed_step_ids: tuple[str, ...] = (),
    as_of: str = "",
    overall_cefr: str = "",
    provider_registry: GrammarActivityProviderRegistry | None = None,
    preferred_provider: GrammarActivityProviderId | None = None,
    skill_registry: SkillExecutorRegistry | None = None,
    execution_guard: ExecutionIdGuard | None = None,
    preferred_skill_executor_id: str | None = None,
    cancel_skill_execution: bool = False,
    cancel_reason: str = "",
) -> StepExecutionResult:
    """Provide ActivitySpecification, then execute exclusively via Skill Executor Registry.

    Blueprint step-kind registry remains for handoff identity (backward compatible
    ``executor_id``). Activity routing never uses activity-type if-branches.
    """
    reg = registry or get_default_registry()
    try:
        step_executor = reg.resolve(step.kind)
    except KeyError as exc:
        raise GrammarRuntimeError(str(exc)) from exc

    context = ActivityExecutionContext(
        blueprint=blueprint,
        step=step,
        runtime=GrammarRuntimeContext(
            lesson_id=lesson_id or blueprint.lesson_id,
            grammar_id=blueprint.grammar_id,
            blueprint_fingerprint=blueprint.fingerprint,
            step_index=step_index,
            completed_step_ids=completed_step_ids,
            as_of=as_of,
        ),
        student=GrammarStudentContext(
            student_id=student_id,
            language_id=language_id,
            overall_cefr=overall_cefr,
        ),
    )
    activity = provide_activity(
        context,
        registry=provider_registry,
        preferred=preferred_provider,
    )
    if not isinstance(activity, ActivitySpecification):
        raise GrammarRuntimeError("Provider must return ActivitySpecification")

    try:
        execution = run_skill_execution(
            activity,
            student_id=student_id,
            language_id=language_id,
            lesson_id=lesson_id or blueprint.lesson_id,
            blueprint_fingerprint=blueprint.fingerprint,
            step_index=step_index,
            overall_cefr=overall_cefr,
            as_of=as_of,
            preferred_executor_id=preferred_skill_executor_id,
            skill_registry=skill_registry,
            guard=execution_guard,
            cancel=cancel_skill_execution,
            cancel_reason=cancel_reason,
        )
    except SkillExecutionBridgeError as exc:
        raise GrammarRuntimeError(f"skill_execution:{exc.code}:{exc.message}") from exc

    if execution.status not in (ExecutionStatus.completed, ExecutionStatus.cancelled):
        raise GrammarRuntimeError(
            f"skill_execution:execution_failure:"
            f"{execution.notes or execution.executor_metadata.executor_id}"
        )

    if cancel_skill_execution:
        success = execution.status is ExecutionStatus.cancelled
    else:
        success = execution.status is ExecutionStatus.completed

    skill_id = execution.executor_metadata.executor_id
    notes = (
        f"placeholder:{step_executor.executor_id}:{step.step_id}"
        f"|activity:{activity.activity_id}"
        f"|skill:{skill_id}"
        f"|execution:{execution.execution_id}"
        f"|status:{execution.status.value}"
    )
    return StepExecutionResult(
        success=success,
        evidence_request=_compat_evidence_request(step, blueprint),
        notes=notes,
        executor_id=step_executor.executor_id,
        activity_specification=activity,
        activity_id=activity.activity_id,
        activity_provider_id=activity.provider_metadata.provider_id,
        skill_executor_id=skill_id,
        execution_id=execution.execution_id,
        execution_result=execution,
        execution_status=execution.status.value,
    )
