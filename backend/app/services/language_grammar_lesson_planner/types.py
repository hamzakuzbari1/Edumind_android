"""Types for Grammar Lesson Planner (G3.1).

GrammarLessonBlueprint.steps is the sole owner of lesson ordering.
Runtime executes steps in order and never invents, reorders, or appends them.
Planner never executes, never calls Claude, never updates mastery/progression.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_grammar.enums import (
    GrammarCEFRBand,
    GrammarLessonStepKind,
    GrammarReinforcementSkill,
)

GRAMMAR_BLUEPRINT_VERSION = "1.0.0"
GRAMMAR_PLANNER_VERSION = "1.0.0"
GRAMMAR_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class GrammarLessonStep:
    """One ordered Blueprint step.

    For reinforcement steps (generic or skill-specific), ``skill`` MUST be set.
    For explanation/practice/warmup/etc., ``skill`` MUST be None.
    """

    kind: GrammarLessonStepKind
    step_id: str
    skill: GrammarReinforcementSkill | None = None
    evidence_eligible: bool = False
    context_hint: str | None = None
    estimated_minutes: int = 0
    title: str = ""


@dataclass(frozen=True, slots=True)
class GrammarPracticeSpec:
    """Detail for practice steps inside a Blueprint."""

    item_count: int = 4
    recommended_contexts: tuple[str, ...] = ()
    focus_note: str = ""


@dataclass(frozen=True, slots=True)
class GrammarEvidencePlan:
    """Which Blueprint step_ids may contribute mastery-eligible evidence."""

    eligible_step_ids: tuple[str, ...] = ()
    min_observations: int = 1
    observation_types_hint: tuple[str, ...] = ("formative",)


@dataclass(frozen=True, slots=True)
class GrammarCompletionCriteria:
    """Deterministic completion gates for Runtime (not scored here)."""

    require_all_steps: bool = True
    require_exit_check: bool = True
    min_evidence_eligible_steps_completed: int = 1
    notes: str = ""


@dataclass(frozen=True, slots=True)
class GrammarPlannerMetadata:
    """Explainable planner decisions — analytics / replay, not Runtime logic."""

    policy_id: str = "default_lesson_v1"
    included_quick_review: bool = False
    review_grammar_id: str | None = None
    reinforcement_skills: tuple[GrammarReinforcementSkill, ...] = ()
    duration_budget_minutes: int = 0
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GrammarLessonBlueprint:
    """Deterministic planner output — Runtime executes ``steps`` only.

    G0 fields (grammar_id, target_cefr, objectives, steps) remain first-class.
    G3.1 adds lesson identity, duration, completion, evidence, versions, freeze.
    """

    grammar_id: str
    target_cefr: GrammarCEFRBand
    objectives: tuple[str, ...]
    steps: tuple[GrammarLessonStep, ...]
    practice_spec: GrammarPracticeSpec = field(default_factory=GrammarPracticeSpec)
    evidence_plan: GrammarEvidencePlan = field(default_factory=GrammarEvidencePlan)
    fingerprint: str = ""
    # G3.1
    lesson_id: str = ""
    lesson_goal: str = ""
    estimated_duration_minutes: int = 0
    completion_criteria: GrammarCompletionCriteria = field(default_factory=GrammarCompletionCriteria)
    planner_metadata: GrammarPlannerMetadata = field(default_factory=GrammarPlannerMetadata)
    blueprint_version: str = GRAMMAR_BLUEPRINT_VERSION
    planner_version: str = GRAMMAR_PLANNER_VERSION
    catalog_version: str = ""
    grammar_schema_version: int = GRAMMAR_SCHEMA_VERSION
    frozen: bool = True
    enabled: bool = True
