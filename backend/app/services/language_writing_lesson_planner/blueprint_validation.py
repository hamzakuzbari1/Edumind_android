"""Blueprint validation (W3.1 FROZEN) — completeness checks only; no LLM."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing_lesson_planner.types import WritingLessonBlueprint


@dataclass(frozen=True, slots=True)
class BlueprintValidationIssue:
    code: str
    message: str


def validate_blueprint(blueprint: WritingLessonBlueprint) -> tuple[BlueprintValidationIssue, ...]:
    """Return issues if blueprint is incomplete — generator must reject invalid blueprints."""
    issues: list[BlueprintValidationIssue] = []

    if not blueprint.blueprint_id:
        issues.append(BlueprintValidationIssue("MISSING_ID", "blueprint_id required"))
    if not blueprint.blueprint_version:
        issues.append(BlueprintValidationIssue("MISSING_VERSION", "blueprint_version required"))
    if not blueprint.schema_version:
        issues.append(BlueprintValidationIssue("MISSING_SCHEMA", "schema_version required"))
    if not blueprint.compatibility_notes:
        issues.append(BlueprintValidationIssue("MISSING_COMPAT", "compatibility_notes required"))
    if not blueprint.blueprint_hash:
        issues.append(BlueprintValidationIssue("MISSING_HASH", "blueprint_hash required"))
    if not blueprint.chain_node_id:
        issues.append(BlueprintValidationIssue("MISSING_NODE", "chain_node_id required"))
    if not blueprint.grammar_targets.primary:
        issues.append(BlueprintValidationIssue("MISSING_GRAMMAR", "grammar primary target required"))
    if not blueprint.vocabulary_targets.primary:
        issues.append(BlueprintValidationIssue("MISSING_VOCAB", "vocabulary primary target required"))
    if not blueprint.learning_outcomes:
        issues.append(BlueprintValidationIssue("MISSING_OUTCOMES", "learning_outcomes required"))
    sc = blueprint.success_criteria
    if sc.min_words <= 0 or sc.max_words < sc.min_words:
        issues.append(BlueprintValidationIssue("INVALID_STRUCTURED_WORDS", "structured min/max words invalid"))
    if not sc.required_grammar:
        issues.append(BlueprintValidationIssue("MISSING_REQUIRED_GRAMMAR", "required_grammar required"))
    if not sc.required_vocabulary:
        issues.append(BlueprintValidationIssue("MISSING_REQUIRED_VOCAB", "required_vocabulary required"))
    if not sc.required_objectives:
        issues.append(BlueprintValidationIssue("MISSING_REQUIRED_OBJECTIVES", "required_objectives required"))
    if not blueprint.success_criteria_labels:
        issues.append(BlueprintValidationIssue("MISSING_CRITERIA_LABELS", "success_criteria_labels required"))
    ep = blueprint.evaluation_plan
    if not ep.required_outcomes:
        issues.append(BlueprintValidationIssue("MISSING_EVAL_OUTCOMES", "evaluation required_outcomes required"))
    if abs(ep.weight_total - 1.0) > 0.01:
        issues.append(BlueprintValidationIssue("INVALID_WEIGHTS", "evaluation weights must sum to 1.0"))
    if not blueprint.difficulty_drivers:
        issues.append(BlueprintValidationIssue("MISSING_DRIVERS", "difficulty_drivers required"))
    if blueprint.min_words <= 0 or blueprint.max_words < blueprint.min_words:
        issues.append(BlueprintValidationIssue("INVALID_WORDS", "min/max word bounds invalid"))
    if blueprint.time_plan.total_minutes <= 0:
        issues.append(BlueprintValidationIssue("INVALID_TIME", "time_plan required"))
    if not blueprint.mission_style:
        issues.append(BlueprintValidationIssue("MISSING_MISSION_STYLE", "mission_style required"))
    if not blueprint.expected_writing_output:
        issues.append(BlueprintValidationIssue("MISSING_OUTPUT", "expected_writing_output required"))

    return tuple(issues)


def blueprint_is_complete(blueprint: WritingLessonBlueprint) -> bool:
    return len(validate_blueprint(blueprint)) == 0
