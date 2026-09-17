"""Types for Speaking Lesson Planner (S9) — blueprint and session contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.services.language_speaking_lesson_planner.mission_types import SpeakingEducationalMission

BLUEPRINT_VERSION = "9.0.0"
BLUEPRINT_SCHEMA_VERSION = "9.0.0"
BLUEPRINT_COMPATIBILITY_NOTES: tuple[str, ...] = (
    "11.0.0: Durable attempt lineage in speaking JSONB; mission/task runtime resolution.",
    "10.1.0: Orthogonal mission taxonomy; adaptive mission plans; explicit executable tasks.",
    "10.0.0: Optional educational_missions foundation (Learn->Notice->Guided->Speak->Feedback).",
    "9.0.0: Adaptive speaking learning journey — plan, session activities, EVI tutoring context.",
)

LANGUAGE_SPEAKING_LESSON_PLANNER_VERSION = BLUEPRINT_VERSION


class SpeakingSessionActivityKind(StrEnum):
    warmup = "warmup"
    target_intro = "target_intro"
    guided_practice = "guided_practice"
    communicative_task = "communicative_task"
    focused_retry = "focused_retry"
    remediation = "remediation"
    reflection = "reflection"


class SpeakingSessionPhase(StrEnum):
    planned = "planned"
    introduced = "introduced"
    guided_practice = "guided_practice"
    communicative_task = "communicative_task"
    evaluated = "evaluated"
    remediation = "remediation"
    focused_retry = "focused_retry"
    reinforced = "reinforced"
    completed = "completed"


class SpeakingSessionOutcomeKind(StrEnum):
    session_complete = "session_complete"
    focused_retry = "focused_retry"
    remediation = "remediation"
    reinforcement = "reinforcement"
    next_target_ready = "next_target_ready"


class SpeakingSessionMode(StrEnum):
    standard = "standard"
    focused_retry = "focused_retry"
    remediation = "remediation"
    reinforcement = "reinforcement"


@dataclass(frozen=True, slots=True)
class SpeakingSessionActivity:
    """One educational step inside a speaking learning session."""

    activity_id: str
    kind: SpeakingSessionActivityKind
    title: str
    learner_instructions: str
    target_skill_ids: tuple[str, ...]
    completion_criteria: tuple[str, ...]
    optional_render_hints: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "activity_id": self.activity_id,
            "kind": self.kind.value,
            "title": self.title,
            "learner_instructions": self.learner_instructions,
            "target_skill_ids": list(self.target_skill_ids),
            "completion_criteria": list(self.completion_criteria),
            "optional_render_hints": list(self.optional_render_hints),
        }


@dataclass(frozen=True, slots=True)
class AlexTutoringContext:
    """Session-scoped EVI tutoring frame — natural conversation, not constant correction."""

    session_goal: str
    target_skill_label: str
    communicative_scenario: str
    encourage_behaviors: tuple[str, ...]
    elicit_behaviors: tuple[str, ...]
    retry_focus: str
    conversation_constraints: tuple[str, ...]
    case_title: str = ""
    case_setting: str = ""
    case_characters: tuple[str, ...] = ()
    case_conflict: str = ""
    case_continuation_hook: str = ""
    case_category: str = ""
    case_archetype: str = ""
    case_stakeholders: tuple[str, ...] = ()
    case_decision_point: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "session_goal": self.session_goal,
            "target_skill_label": self.target_skill_label,
            "communicative_scenario": self.communicative_scenario,
            "encourage_behaviors": list(self.encourage_behaviors),
            "elicit_behaviors": list(self.elicit_behaviors),
            "retry_focus": self.retry_focus,
            "conversation_constraints": list(self.conversation_constraints),
            "case_title": self.case_title,
            "case_setting": self.case_setting,
            "case_characters": list(self.case_characters),
            "case_conflict": self.case_conflict,
            "case_continuation_hook": self.case_continuation_hook,
            "case_category": self.case_category,
            "case_archetype": self.case_archetype,
            "case_stakeholders": list(self.case_stakeholders),
            "case_decision_point": self.case_decision_point,
        }


@dataclass(frozen=True, slots=True)
class SpeakingLessonBlueprint:
    """Deterministic plan contract between diagnostic and session runtime (S9)."""

    blueprint_id: str
    blueprint_version: str
    schema_version: str
    compatibility_notes: tuple[str, ...]
    blueprint_hash: str
    recommendation_id: str
    session_goal: str
    target_skill_ids: tuple[str, ...]
    primary_target_skill_id: str
    selection_reason: str
    reason_detail: str
    evidence_basis: tuple[str, ...]
    session_mode: SpeakingSessionMode
    official_cefr_hint: str
    speaking_goal: str
    activities: tuple[SpeakingSessionActivity, ...]
    alex_context: AlexTutoringContext
    completion_evidence_requirements: tuple[str, ...]
    remediation_strategy: str
    retry_strategy: str
    min_communicative_turns: int
    planner_version: str = BLUEPRINT_VERSION
    # S10/S11 educational mission foundation — optional, backward-compatible extension.
    # The frozen 5-step `activities` sequence remains the current executable cursor;
    # missions/tasks are resolved via mission_task_resolver and attempt_lineage.
    educational_missions: tuple[SpeakingEducationalMission, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "blueprint_id": self.blueprint_id,
            "blueprint_version": self.blueprint_version,
            "schema_version": self.schema_version,
            "compatibility_notes": list(self.compatibility_notes),
            "blueprint_hash": self.blueprint_hash,
            "recommendation_id": self.recommendation_id,
            "session_goal": self.session_goal,
            "target_skill_ids": list(self.target_skill_ids),
            "primary_target_skill_id": self.primary_target_skill_id,
            "selection_reason": self.selection_reason,
            "reason_detail": self.reason_detail,
            "evidence_basis": list(self.evidence_basis),
            "session_mode": self.session_mode.value,
            "official_cefr_hint": self.official_cefr_hint,
            "speaking_goal": self.speaking_goal,
            "activities": [a.to_dict() for a in self.activities],
            "alex_context": self.alex_context.to_dict(),
            "completion_evidence_requirements": list(self.completion_evidence_requirements),
            "remediation_strategy": self.remediation_strategy,
            "retry_strategy": self.retry_strategy,
            "min_communicative_turns": self.min_communicative_turns,
            "planner_version": self.planner_version,
            "educational_missions": [m.to_dict() for m in self.educational_missions],
        }


@dataclass
class SpeakingTurnAccumulation:
    """Canonical turn summary accumulated within one learning session."""

    live_turn_id: str
    target_skill_id: str
    performance: float
    success: bool
    source_dimension: str
    mistake_tags: tuple[str, ...]
    mutation_applied: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "live_turn_id": self.live_turn_id,
            "target_skill_id": self.target_skill_id,
            "performance": round(self.performance, 4),
            "success": self.success,
            "source_dimension": self.source_dimension,
            "mistake_tags": list(self.mistake_tags),
            "mutation_applied": self.mutation_applied,
        }


@dataclass
class SpeakingLearningSession:
    """Educational session state machine instance (S9 orchestration)."""

    session_id: str
    blueprint_id: str
    phase: SpeakingSessionPhase
    session_mode: SpeakingSessionMode
    current_activity_id: str
    completed_activity_ids: list[str]
    live_session_id: str
    turn_accumulations: list[SpeakingTurnAccumulation]
    communicative_turns_completed: int
    started_at: str
    updated_at: str
    outcome_kind: SpeakingSessionOutcomeKind | None = None
    outcome_detail: str = ""
    next_recommendation_summary: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "blueprint_id": self.blueprint_id,
            "phase": self.phase.value,
            "session_mode": self.session_mode.value,
            "current_activity_id": self.current_activity_id,
            "completed_activity_ids": list(self.completed_activity_ids),
            "live_session_id": self.live_session_id,
            "turn_accumulations": [t.to_dict() for t in self.turn_accumulations],
            "communicative_turns_completed": self.communicative_turns_completed,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "outcome_kind": self.outcome_kind.value if self.outcome_kind else None,
            "outcome_detail": self.outcome_detail,
            "next_recommendation_summary": self.next_recommendation_summary,
        }


@dataclass(frozen=True, slots=True)
class SpeakingSessionDecision:
    """Deterministic educational decision at a session boundary."""

    decision_id: str
    outcome_kind: SpeakingSessionOutcomeKind
    detail: str
    provenance: tuple[str, ...]
    next_phase: SpeakingSessionPhase
    retry_same_target: bool
    student_summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "outcome_kind": self.outcome_kind.value,
            "detail": self.detail,
            "provenance": list(self.provenance),
            "next_phase": self.next_phase.value,
            "retry_same_target": self.retry_same_target,
            "student_summary": self.student_summary,
        }


@dataclass(frozen=True, slots=True)
class SpeakingLearningPlan:
    """Active speaking learning plan pointer — not a second skill graph."""

    plan_id: str
    active_blueprint_id: str
    primary_target_skill_id: str
    primary_target_label: str
    selection_reason: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "active_blueprint_id": self.active_blueprint_id,
            "primary_target_skill_id": self.primary_target_skill_id,
            "primary_target_label": self.primary_target_label,
            "selection_reason": self.selection_reason,
            "updated_at": self.updated_at,
        }
