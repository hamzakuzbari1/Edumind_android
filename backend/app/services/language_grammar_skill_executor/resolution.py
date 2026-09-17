"""Deterministic Skill Executor resolution (G3.4).

Runtime must never contain activity-type if-branches — Registry resolves.
"""

from __future__ import annotations

from app.services.language_grammar_activity_spec.registry import get_default_spec_registry
from app.services.language_grammar_skill_executor.errors import (
    MissingExecutorError,
    SkillExecutorError,
)
from app.services.language_grammar_skill_executor.registry import (
    SkillExecutorRegistry,
    get_default_skill_executor_registry,
)
from app.services.language_grammar_skill_executor.types import ExecutionContext, SkillExecutor


def resolve_executor(
    context: ExecutionContext,
    *,
    registry: SkillExecutorRegistry | None = None,
    preferred_executor_id: str | None = None,
) -> SkillExecutor:
    """Select a SkillExecutor deterministically for the ActivitySpecification."""
    reg = registry or get_default_skill_executor_registry()
    activity_type = context.specification.activity_type

    if not get_default_spec_registry().is_activity_type_known(activity_type):
        raise SkillExecutorError(f"Unknown activity type: {activity_type}")

    preferred = (preferred_executor_id or context.metadata.preferred_executor_id or "").strip()
    if preferred:
        try:
            return reg.get(preferred)
        except KeyError as exc:
            raise MissingExecutorError(f"Preferred executor not registered: {preferred}") from exc

    mapped = reg.preferred_executor_id_for(activity_type)
    if mapped:
        try:
            executor = reg.get(mapped)
        except KeyError as exc:
            raise MissingExecutorError(
                f"Mapped executor not registered for {activity_type}: {mapped}"
            ) from exc
        if executor.supports(activity_type):
            return executor

    supporting = reg.find_supporting(activity_type)
    if supporting:
        return supporting[0]

    raise MissingExecutorError(
        f"No skill executor registered for activity_type={activity_type!r}"
    )
