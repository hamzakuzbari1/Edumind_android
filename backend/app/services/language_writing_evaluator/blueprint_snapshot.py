"""Blueprint snapshot for evaluator (W7) — distilled from persisted blueprint; no lesson_planner import in evaluator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvaluationPlanSnapshot:
    grammar_weight: float
    vocabulary_weight: float
    organization_weight: float
    task_completion_weight: float
    goal_alignment_weight: float
    required_outcomes: tuple[str, ...]
    critical_mistakes: tuple[str, ...]
    stretch_bonus_criteria: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SuccessCriteriaSnapshot:
    min_words: int
    max_words: int
    required_grammar: tuple[str, ...]
    required_vocabulary: tuple[str, ...]
    required_objectives: tuple[str, ...]
    required_output_format: str
    success_criteria_labels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvaluatorBlueprintSnapshot:
    """Evaluator input derived from Lesson Blueprint — weights are never recomputed at runtime."""

    blueprint_version: str
    blueprint_hash: str
    generation_hash: str
    chain_id: str
    chain_node_id: str
    task_type: str
    genre: str
    personal_goal: str
    learning_outcomes: tuple[str, ...]
    common_mistakes: tuple[str, ...]
    difficulty_drivers: tuple[str, ...]
    grammar_primary: str
    grammar_secondary: str
    vocabulary_primary: tuple[str, ...]
    evaluation_plan: EvaluationPlanSnapshot
    success_criteria: SuccessCriteriaSnapshot
    narrative_why: str = ""


def blueprint_snapshot_from_dict(blueprint: dict[str, object], *, generation_hash: str = "") -> EvaluatorBlueprintSnapshot:
    """Build evaluator snapshot from persisted writing_blueprint body_json."""
    ep = blueprint.get("evaluation_plan") or {}
    sc = blueprint.get("success_criteria") or {}
    gt = blueprint.get("grammar_targets") or {}
    vt = blueprint.get("vocabulary_targets") or {}
    return EvaluatorBlueprintSnapshot(
        blueprint_version=str(blueprint.get("blueprint_version") or ""),
        blueprint_hash=str(blueprint.get("blueprint_hash") or ""),
        generation_hash=generation_hash,
        chain_id=str(blueprint.get("chain_id") or ""),
        chain_node_id=str(blueprint.get("chain_node_id") or ""),
        task_type=str(blueprint.get("task_type") or ""),
        genre=str(blueprint.get("genre") or ""),
        personal_goal=str(blueprint.get("personal_goal") or ""),
        learning_outcomes=tuple(blueprint.get("learning_outcomes") or ()),
        common_mistakes=tuple(blueprint.get("common_mistakes") or ()),
        difficulty_drivers=tuple(blueprint.get("difficulty_drivers") or ()),
        grammar_primary=str(gt.get("primary") or ""),
        grammar_secondary=str(gt.get("secondary") or ""),
        vocabulary_primary=tuple(vt.get("primary") or ()),
        evaluation_plan=EvaluationPlanSnapshot(
            grammar_weight=float(ep.get("grammar_weight") or 0.2),
            vocabulary_weight=float(ep.get("vocabulary_weight") or 0.2),
            organization_weight=float(ep.get("organization_weight") or 0.2),
            task_completion_weight=float(ep.get("task_completion_weight") or 0.2),
            goal_alignment_weight=float(ep.get("goal_alignment_weight") or 0.2),
            required_outcomes=tuple(ep.get("required_outcomes") or ()),
            critical_mistakes=tuple(ep.get("critical_mistakes") or ()),
            stretch_bonus_criteria=tuple(ep.get("stretch_bonus_criteria") or ()),
        ),
        success_criteria=SuccessCriteriaSnapshot(
            min_words=int(sc.get("min_words") or 0),
            max_words=int(sc.get("max_words") or 9999),
            required_grammar=tuple(sc.get("required_grammar") or ()),
            required_vocabulary=tuple(sc.get("required_vocabulary") or ()),
            required_objectives=tuple(sc.get("required_objectives") or ()),
            required_output_format=str(sc.get("required_output_format") or ""),
            success_criteria_labels=tuple(blueprint.get("success_criteria_labels") or ()),
        ),
        narrative_why=str(blueprint.get("narrative_why") or ""),
    )
