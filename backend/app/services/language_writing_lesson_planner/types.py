"""Types for Writing Lesson Planner (W3.1 FROZEN) — blueprint is the planner→generator contract."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing.enums import (
    ContextComplexity,
    ExpectedWritingOutput,
    LexisCategory,
    OfficialWritingCEFR,
    WritingArc,
    WritingCoachPersonality,
    WritingGoal,
    WritingMissionStyle,
    WritingTopicId,
)
from app.services.language_writing_curriculum.types import WritingGoalProfile
from app.services.language_writing_grammar_progression.types import GrammarProgressionSnapshot
from app.services.language_writing_knowledge_chain.types import WritingKnowledgeChainNode
from app.services.language_writing_lexis_progression.types import LexisProgressionSnapshot

BLUEPRINT_VERSION = "3.1.0"
BLUEPRINT_SCHEMA_VERSION = "3.1.0"
BLUEPRINT_COMPATIBILITY_NOTES: tuple[str, ...] = (
    "3.1.0: Added evaluation_plan, structured success_criteria, blueprint_hash, versioning.",
    "3.0.0: Initial lesson blueprint contract between planner and generator.",
    "Future evaluators must read evaluation_plan from blueprint — do not recompute weights at runtime.",
)


@dataclass(frozen=True, slots=True)
class GrammarTargets:
    """Grammar targets for one lesson — planner-owned."""

    primary: str
    secondary: str
    review: str
    stretch: str = ""


@dataclass(frozen=True, slots=True)
class VocabularyTargets:
    """Vocabulary targets for one lesson — planner-owned."""

    primary: tuple[str, ...]
    secondary: tuple[str, ...]
    review: tuple[str, ...]
    stretch: tuple[str, ...] = ()
    categories: tuple[LexisCategory, ...] = ()


@dataclass(frozen=True, slots=True)
class LessonTimePlan:
    """Estimated time — derived from node + goal profile."""

    writing_minutes: int
    revision_minutes: int
    total_minutes: int


@dataclass(frozen=True, slots=True)
class EvaluationPlan:
    """Structured rubric plan for future Writing Evaluator (W3.1).

    Weights are planner-owned. Evaluator phases must reuse this plan verbatim.
    """

    grammar_weight: float
    vocabulary_weight: float
    organization_weight: float
    task_completion_weight: float
    goal_alignment_weight: float
    required_outcomes: tuple[str, ...]
    critical_mistakes: tuple[str, ...]
    stretch_bonus_criteria: tuple[str, ...]

    @property
    def weight_total(self) -> float:
        return (
            self.grammar_weight
            + self.vocabulary_weight
            + self.organization_weight
            + self.task_completion_weight
            + self.goal_alignment_weight
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "grammar_weight": round(self.grammar_weight, 4),
            "vocabulary_weight": round(self.vocabulary_weight, 4),
            "organization_weight": round(self.organization_weight, 4),
            "task_completion_weight": round(self.task_completion_weight, 4),
            "goal_alignment_weight": round(self.goal_alignment_weight, 4),
            "required_outcomes": list(self.required_outcomes),
            "critical_mistakes": list(self.critical_mistakes),
            "stretch_bonus_criteria": list(self.stretch_bonus_criteria),
        }


@dataclass(frozen=True, slots=True)
class StructuredSuccessCriteria:
    """Structured educational checkpoints — not free-form text only."""

    min_words: int
    max_words: int
    required_grammar: tuple[str, ...]
    required_vocabulary: tuple[str, ...]
    required_output_format: ExpectedWritingOutput
    required_objectives: tuple[str, ...]
    optional_stretch_objectives: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "min_words": self.min_words,
            "max_words": self.max_words,
            "required_grammar": list(self.required_grammar),
            "required_vocabulary": list(self.required_vocabulary),
            "required_output_format": self.required_output_format.value,
            "required_objectives": list(self.required_objectives),
            "optional_stretch_objectives": list(self.optional_stretch_objectives),
        }


def success_criteria_labels(criteria: StructuredSuccessCriteria) -> tuple[str, ...]:
    """Human-readable checklist labels derived from structured criteria."""
    labels: list[str] = [
        f"Write at least {criteria.min_words} words (max {criteria.max_words})",
    ]
    for g in criteria.required_grammar:
        labels.append(f"Use {g.replace('_', ' ')} correctly")
    if criteria.required_vocabulary:
        labels.append(f"Include vocabulary: {', '.join(criteria.required_vocabulary[:4])}")
    labels.append(f"Output format: {criteria.required_output_format.value}")
    for obj in criteria.required_objectives:
        labels.append(f"Complete objective: {obj}")
    return tuple(labels)


@dataclass(frozen=True, slots=True)
class WritingLessonBlueprint:
    """Canonical contract between Lesson Planner and Writing Generator (W3.1 FROZEN)."""

    blueprint_id: str
    blueprint_version: str
    schema_version: str
    compatibility_notes: tuple[str, ...]
    blueprint_hash: str
    # Placement
    official_cefr: OfficialWritingCEFR
    personal_goal: WritingGoal
    goal_profile_label: str
    topic_id: WritingTopicId
    chain_id: str
    chain_node_id: str
    chain_position: int
    curriculum_arc: WritingArc
    context_complexity: ContextComplexity
    # Educational targets (planner-owned)
    task_type: str
    genre: str
    grammar_targets: GrammarTargets
    vocabulary_targets: VocabularyTargets
    mission_style: WritingMissionStyle
    expected_writing_output: ExpectedWritingOutput
    difficulty_drivers: tuple[str, ...]
    learning_outcomes: tuple[str, ...]
    success_criteria: StructuredSuccessCriteria
    success_criteria_labels: tuple[str, ...]
    evaluation_plan: EvaluationPlan
    common_mistakes: tuple[str, ...]
    review_targets: tuple[str, ...]
    stretch_targets: tuple[str, ...]
    time_plan: LessonTimePlan
    min_words: int
    max_words: int
    # Coach / mission framing (from frozen W2 goal + node)
    coach_personality: WritingCoachPersonality
    narrative_why: str
    carry_forward_context: str
    planner_version: str = BLUEPRINT_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "blueprint_id": self.blueprint_id,
            "blueprint_version": self.blueprint_version,
            "schema_version": self.schema_version,
            "compatibility_notes": list(self.compatibility_notes),
            "blueprint_hash": self.blueprint_hash,
            "official_cefr": self.official_cefr.value,
            "personal_goal": self.personal_goal.value,
            "goal_profile_label": self.goal_profile_label,
            "topic_id": self.topic_id.value,
            "chain_id": self.chain_id,
            "chain_node_id": self.chain_node_id,
            "chain_position": self.chain_position,
            "curriculum_arc": self.curriculum_arc.value,
            "context_complexity": int(self.context_complexity),
            "task_type": self.task_type,
            "genre": self.genre,
            "grammar_targets": {
                "primary": self.grammar_targets.primary,
                "secondary": self.grammar_targets.secondary,
                "review": self.grammar_targets.review,
                "stretch": self.grammar_targets.stretch,
            },
            "vocabulary_targets": {
                "primary": list(self.vocabulary_targets.primary),
                "secondary": list(self.vocabulary_targets.secondary),
                "review": list(self.vocabulary_targets.review),
                "stretch": list(self.vocabulary_targets.stretch),
                "categories": [c.value for c in self.vocabulary_targets.categories],
            },
            "mission_style": self.mission_style.value,
            "expected_writing_output": self.expected_writing_output.value,
            "difficulty_drivers": list(self.difficulty_drivers),
            "learning_outcomes": list(self.learning_outcomes),
            "success_criteria": self.success_criteria.to_dict(),
            "success_criteria_labels": list(self.success_criteria_labels),
            "evaluation_plan": self.evaluation_plan.to_dict(),
            "common_mistakes": list(self.common_mistakes),
            "review_targets": list(self.review_targets),
            "stretch_targets": list(self.stretch_targets),
            "time_plan": {
                "writing_minutes": self.time_plan.writing_minutes,
                "revision_minutes": self.time_plan.revision_minutes,
                "total_minutes": self.time_plan.total_minutes,
            },
            "min_words": self.min_words,
            "max_words": self.max_words,
            "coach_personality": self.coach_personality.value,
            "narrative_why": self.narrative_why,
            "carry_forward_context": self.carry_forward_context,
            "planner_version": self.planner_version,
        }


@dataclass(frozen=True, slots=True)
class LessonPlannerInput:
    """All upstream context for deterministic planning — no LLM."""

    official_cefr: OfficialWritingCEFR
    goal_profile: WritingGoalProfile
    selected_node: WritingKnowledgeChainNode
    grammar_snapshot: GrammarProgressionSnapshot | None = None
    lexis_snapshot: LexisProgressionSnapshot | None = None
    completed_node_ids: frozenset[str] = frozenset()
    blueprint_id: str = ""


@dataclass(frozen=True, slots=True)
class LessonPlannerResult:
    """Planner output — blueprint only."""

    blueprint: WritingLessonBlueprint
    selection_reason: str
    planner_version: str = BLUEPRINT_VERSION


GENERATOR_FORBIDDEN_DECISIONS: frozenset[str] = frozenset(
    {
        "topic_id",
        "chain_id",
        "chain_node_id",
        "context_complexity",
        "grammar_targets",
        "vocabulary_targets",
        "personal_goal",
        "curriculum_arc",
        "expected_writing_output",
        "mission_style",
        "coach_personality",
        "learning_outcomes",
        "success_criteria",
        "evaluation_plan",
        "difficulty_drivers",
        "min_words",
        "max_words",
    }
)

GENERATOR_FORBIDDEN_CONTEXT_SOURCES: frozenset[str] = frozenset(
    {
        "student",
        "student_id",
        "progression",
        "topic_universe",
        "goal_profile",
        "goal_profiles",
        "grammar_progression",
        "vocabulary_progression",
        "lexis_progression",
        "knowledge_chain",
        "curriculum_selection",
        "LessonPlannerInput",
    }
)

DETERMINISM_CANONICAL_FIELDS: frozenset[str] = frozenset(
    {
        "blueprint_hash",
        "blueprint_version",
        "schema_version",
        "chain_node_id",
        "personal_goal",
        "grammar_targets",
        "vocabulary_targets",
        "learning_outcomes",
        "success_criteria",
        "evaluation_plan",
        "expected_writing_output",
        "context_complexity",
        "curriculum_arc",
    }
)
