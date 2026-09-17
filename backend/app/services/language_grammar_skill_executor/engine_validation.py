"""Validation for Skill Execution Engine (V1.5)."""

from __future__ import annotations

from app.services.language_grammar.id_canon import is_canonical_grammar_id, normalize_grammar_id
from app.services.language_grammar_activity_spec import (
    ActivitySpecError,
    ActivitySpecification,
    validate_activity_specification,
)
from app.services.language_grammar_skill_executor.errors import (
    BrokenSpecificationError,
    MissingExecutorError,
    SkillExecutorError,
)
from app.services.language_grammar_skill_executor.registry import SkillExecutorRegistry
from app.services.language_grammar_skill_executor.session import ExecutionSession, SessionStatus
from app.services.language_grammar_skill_executor.state_machine import assert_session_transition


def validate_specification(specification: ActivitySpecification) -> None:
    try:
        validate_activity_specification(specification)
    except ActivitySpecError as exc:
        raise BrokenSpecificationError(str(exc)) from exc
    if not specification.grammar_targets and not specification.grammar_topic:
        raise BrokenSpecificationError("ActivitySpecification missing grammar_targets")


def validate_grammar_targets(grammar_targets: tuple[str, ...]) -> None:
    if not grammar_targets:
        raise SkillExecutorError("grammar_targets required")
    for raw in grammar_targets:
        gid = normalize_grammar_id(raw)
        if not is_canonical_grammar_id(gid):
            raise SkillExecutorError(f"Invalid grammar_id: {raw!r}")


def validate_executor_available(
    registry: SkillExecutorRegistry,
    *,
    activity_type: str,
    preferred_executor_id: str = "",
) -> str:
    if preferred_executor_id:
        try:
            registry.get(preferred_executor_id)
            return preferred_executor_id
        except KeyError as exc:
            raise MissingExecutorError(
                f"Preferred executor not registered: {preferred_executor_id}"
            ) from exc

    mapped = registry.preferred_executor_id_for(activity_type)
    if mapped:
        try:
            registry.get(mapped)
            return mapped
        except KeyError as exc:
            raise MissingExecutorError(
                f"Mapped executor not registered for {activity_type}: {mapped}"
            ) from exc

    supporting = registry.find_supporting(activity_type)
    if supporting:
        return supporting[0].executor_id
    raise MissingExecutorError(f"No executor registered for activity_type={activity_type!r}")


def validate_session_transition(session: ExecutionSession, target: SessionStatus) -> None:
    assert_session_transition(session.status, target)
