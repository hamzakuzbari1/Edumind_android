"""Blueprint validation (G3.1) — reject broken / impossible plans."""

from __future__ import annotations

from app.services.language_grammar.enums import GrammarLessonStepKind, GrammarReinforcementSkill
from app.services.language_grammar_integration.types import GrammarLearningSnapshot
from app.services.language_grammar_lesson_planner.policies import STEP_ORDER_RANK
from app.services.language_grammar_lesson_planner.types import GrammarLessonBlueprint, GrammarLessonStep

_REINFORCEMENT_KINDS = frozenset(
    {
        GrammarLessonStepKind.reinforcement,
        GrammarLessonStepKind.reading_reinforcement,
        GrammarLessonStepKind.listening_reinforcement,
        GrammarLessonStepKind.writing_reinforcement,
        GrammarLessonStepKind.speaking_reinforcement,
    }
)

_SKILL_KINDS = {
    GrammarLessonStepKind.reading_reinforcement: GrammarReinforcementSkill.reading,
    GrammarLessonStepKind.listening_reinforcement: GrammarReinforcementSkill.listening,
    GrammarLessonStepKind.writing_reinforcement: GrammarReinforcementSkill.writing,
    GrammarLessonStepKind.speaking_reinforcement: GrammarReinforcementSkill.speaking,
}


class GrammarPlannerError(ValueError):
    """Invalid planner input or blueprint."""


def validate_snapshot_for_planning(snapshot: GrammarLearningSnapshot) -> None:
    if not snapshot.enabled:
        raise GrammarPlannerError("Learning snapshot disabled")
    if not snapshot.current_grammar_id:
        raise GrammarPlannerError("Missing current grammar topic")
    if snapshot.current_topic is None:
        raise GrammarPlannerError("Missing current topic metadata")
    if snapshot.current_topic.grammar_id != snapshot.current_grammar_id:
        raise GrammarPlannerError("Current topic metadata mismatch")
    if not snapshot.catalog_version:
        raise GrammarPlannerError("Missing catalog_version in snapshot")


def _validate_step(step: GrammarLessonStep, *, seen_ids: set[str]) -> None:
    if not step.step_id or not str(step.step_id).strip():
        raise GrammarPlannerError("Missing step_id")
    if step.step_id in seen_ids:
        raise GrammarPlannerError(f"Duplicate step_id: {step.step_id}")
    seen_ids.add(step.step_id)

    if step.kind in _REINFORCEMENT_KINDS:
        if step.skill is None:
            raise GrammarPlannerError(f"Reinforcement step {step.step_id} missing skill")
        expected = _SKILL_KINDS.get(step.kind)
        if expected is not None and step.skill is not expected:
            raise GrammarPlannerError(
                f"Broken reinforcement selection: {step.kind} requires {expected}, got {step.skill}"
            )
    elif step.skill is not None:
        raise GrammarPlannerError(f"Non-reinforcement step {step.step_id} must not set skill")


def validate_blueprint(
    blueprint: GrammarLessonBlueprint,
    *,
    snapshot: GrammarLearningSnapshot | None = None,
) -> None:
    if not blueprint.grammar_id:
        raise GrammarPlannerError("Unknown / missing grammar topic on blueprint")
    if snapshot is not None:
        meta = snapshot.topic_meta(blueprint.grammar_id)
        if meta is None and (
            snapshot.current_topic is None
            or snapshot.current_topic.grammar_id != blueprint.grammar_id
        ):
            raise GrammarPlannerError(f"Unknown topic: {blueprint.grammar_id}")

    if not blueprint.lesson_goal and not blueprint.objectives:
        raise GrammarPlannerError("Missing lesson goal / objectives")
    if not blueprint.steps:
        raise GrammarPlannerError("Missing steps")
    if blueprint.estimated_duration_minutes <= 0:
        raise GrammarPlannerError("Missing / invalid duration")
    if blueprint.completion_criteria is None:
        raise GrammarPlannerError("Missing completion criteria")
    if not blueprint.blueprint_version or not blueprint.planner_version:
        raise GrammarPlannerError("Missing version fields")
    if not blueprint.catalog_version:
        raise GrammarPlannerError("Missing catalog_version")
    if not blueprint.frozen:
        raise GrammarPlannerError("Blueprint must be frozen")

    seen: set[str] = set()
    prev_rank = -1
    for step in blueprint.steps:
        _validate_step(step, seen_ids=seen)
        rank = STEP_ORDER_RANK.get(step.kind)
        if rank is None:
            raise GrammarPlannerError(f"Unknown step kind: {step.kind}")
        if rank < prev_rank:
            raise GrammarPlannerError(
                f"Impossible step ordering: {step.kind} after higher-rank step"
            )
        prev_rank = rank

    kinds = [s.kind for s in blueprint.steps]
    if GrammarLessonStepKind.explanation not in kinds:
        raise GrammarPlannerError("Missing explanation step")
    if GrammarLessonStepKind.practice not in kinds:
        raise GrammarPlannerError("Missing practice step")
    if blueprint.completion_criteria.require_exit_check:
        if GrammarLessonStepKind.exit_check not in kinds:
            raise GrammarPlannerError("Missing exit_check required by completion criteria")

    eligible = {s.step_id for s in blueprint.steps if s.evidence_eligible}
    planned = set(blueprint.evidence_plan.eligible_step_ids)
    if not planned:
        raise GrammarPlannerError("Missing evidence expectations")
    if not planned.issubset(eligible):
        raise GrammarPlannerError("Evidence plan references non-eligible steps")
