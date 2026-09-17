"""S10.1 educational mission foundation contracts (lesson_planner ownership).

These contracts let a speaking learning session represent an adaptive educational path,
e.g. Learn -> Notice -> Guided Practice -> Speak -> Feedback (with Transfer / Retention
only when a planning signal calls for them).

Scope is CONTRACTS ONLY:
- no stage / official CEFR / promotion mutation
- no durable attempt lineage or persistence (S11 owns that)
- no EVI budget enforcement

S10.1 corrections over S10:
- `SpeakingMissionKind` is educational purpose only (execution modes and `retry` removed).
- The `(mission_kind, execution_mode, evidence_intent)` triple is validated by the
  dataclass invariant against the canonical taxonomy legality boundary.
- Retry is a runtime flow decision (`SpeakingMissionOutcome`), not a mission or a
  mission-to-mission pointer. `retry_of_mission_id` is removed.
- Transfer is modelled by a distinct executable task with a changed context descriptor,
  not by a `transfer_of_mission_id` pointer. `transfer_of_mission_id` is removed.
- Executable vs content-only missions are explicit via typed `tasks`, not an empty
  `activity_ref` string.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.services.language_speaking.enums import (
    SpeakingEvidenceIntent,
    SpeakingExecutionMode,
    SpeakingMissionKind,
    SpeakingTeachingBlockKind,
)
from app.services.language_speaking_lesson_planner.task_taxonomy import validate_mission_combination

EDUCATIONAL_MISSION_SCHEMA_VERSION = "10.1.0"


class SpeakingMissionOutcome(StrEnum):
    """Contract-level runtime FLOW decision for a mission's task (not a mission kind).

    This models what should happen after a task attempt is evaluated. It is the home for
    retry semantics: retry is a flow decision here, never an educational phase and never
    a pre-emitted mission. Durable attempt/retry lineage is deferred to S11.

    Relationship to the session-boundary enum `SpeakingSessionOutcomeKind` (owned by
    decision_rules): session outcomes are per-session; mission outcomes are per
    mission-task. `decision_rules.mission_flow_from_session_outcome()` maps between them
    so the two are not duplicated.
    """

    proceed = "continue"
    retry_same_task = "retry_same_task"
    retry_with_scaffold = "retry_with_scaffold"
    move_to_transfer = "move_to_transfer"
    complete = "complete"


@dataclass(frozen=True, slots=True)
class SpeakingLearningObjective:
    """Typed learning objective attachable to a mission or session."""

    objective_id: str
    target_skill_id: str
    student_objective_text: str
    expected_outcome: str
    evidence_expectation: SpeakingEvidenceIntent
    prerequisite_skill_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "objective_id": self.objective_id,
            "target_skill_id": self.target_skill_id,
            "student_objective_text": self.student_objective_text,
            "expected_outcome": self.expected_outcome,
            "evidence_expectation": self.evidence_expectation.value,
            "prerequisite_skill_ids": list(self.prerequisite_skill_ids),
        }

    def to_student_dict(self) -> dict[str, object]:
        return {
            "objective_id": self.objective_id,
            "student_objective_text": self.student_objective_text,
            "expected_outcome": self.expected_outcome,
        }


@dataclass(frozen=True, slots=True)
class SpeakingTeachingBlock:
    """Typed teaching content. `is_evidence` is False by default — teaching content is
    never automatically treated as speaking evidence (S8 owns evidence application)."""

    block_id: str
    kind: SpeakingTeachingBlockKind
    title: str
    body: str
    target_skill_ids: tuple[str, ...] = ()
    is_evidence: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "block_id": self.block_id,
            "kind": self.kind.value,
            "title": self.title,
            "body": self.body,
            "target_skill_ids": list(self.target_skill_ids),
            "is_evidence": self.is_evidence,
        }

    def to_student_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "title": self.title,
            "body": self.body,
        }


@dataclass(frozen=True, slots=True)
class SpeakingExecutableTask:
    """The executable student assignment inside a mission (S10.1).

    Replaces the ambiguous empty `activity_ref`. A mission is executable iff it has at
    least one task. `task_id` is a stable definition identity (blueprint-scoped). For a
    transfer task, `context_descriptor` names the changed task/context; skill-transfer
    EVIDENCE itself remains authoritative in S2/S7 across `context_id`, not here.
    `legacy_activity_ref` bridges to a current S9 activity when one exists (else empty).
    """

    task_id: str
    execution_mode: SpeakingExecutionMode
    evidence_intent: SpeakingEvidenceIntent
    prompt: str
    target_skill_ids: tuple[str, ...] = ()
    context_descriptor: str = ""
    legacy_activity_ref: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "execution_mode": self.execution_mode.value,
            "evidence_intent": self.evidence_intent.value,
            "prompt": self.prompt,
            "target_skill_ids": list(self.target_skill_ids),
            "context_descriptor": self.context_descriptor,
            "legacy_activity_ref": self.legacy_activity_ref,
        }

    def to_student_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "execution_mode": self.execution_mode.value,
            "prompt": self.prompt,
            "context_descriptor": self.context_descriptor,
        }


@dataclass(frozen=True, slots=True)
class SpeakingEducationalMission:
    """One educational mission inside a learning session (S10.1).

    Three orthogonal taxonomy dimensions, validated against the canonical taxonomy at
    construction time (dataclass invariant):
    - `mission_kind`    : educational phase / purpose (dimension A)
    - `execution_mode`  : how it runs (dimension B)
    - `evidence_intent` : why evidence is collected (dimension C)

    `retry_policy` declares what to do if this mission's task underperforms. It does NOT
    create a retry mission and carries no lineage. Executable structure is explicit via
    `tasks` (empty => content/review-only mission).
    """

    mission_id: str
    mission_kind: SpeakingMissionKind
    execution_mode: SpeakingExecutionMode
    evidence_intent: SpeakingEvidenceIntent
    order_index: int
    title: str
    learner_instructions: str
    objectives: tuple[SpeakingLearningObjective, ...] = ()
    target_skill_ids: tuple[str, ...] = ()
    teaching_blocks: tuple[SpeakingTeachingBlock, ...] = ()
    tasks: tuple[SpeakingExecutableTask, ...] = ()
    retry_policy: SpeakingMissionOutcome = SpeakingMissionOutcome.proceed

    def __post_init__(self) -> None:
        # Single canonical legality boundary — illegal triples fail deterministically.
        validate_mission_combination(self.mission_kind, self.execution_mode, self.evidence_intent)

    @property
    def is_executable(self) -> bool:
        return len(self.tasks) > 0

    @property
    def is_content_only(self) -> bool:
        return not self.tasks

    def to_dict(self) -> dict[str, object]:
        return {
            "mission_id": self.mission_id,
            "mission_kind": self.mission_kind.value,
            "execution_mode": self.execution_mode.value,
            "evidence_intent": self.evidence_intent.value,
            "order_index": self.order_index,
            "title": self.title,
            "learner_instructions": self.learner_instructions,
            "objectives": [o.to_dict() for o in self.objectives],
            "target_skill_ids": list(self.target_skill_ids),
            "teaching_blocks": [b.to_dict() for b in self.teaching_blocks],
            "tasks": [t.to_dict() for t in self.tasks],
            "retry_policy": self.retry_policy.value,
            "is_executable": self.is_executable,
        }

    def to_student_dict(self) -> dict[str, object]:
        return {
            "mission_id": self.mission_id,
            "mission_kind": self.mission_kind.value,
            "execution_mode": self.execution_mode.value,
            "order_index": self.order_index,
            "title": self.title,
            "learner_instructions": self.learner_instructions,
            "is_executable": self.is_executable,
            "objectives": [o.to_student_dict() for o in self.objectives],
            "teaching_blocks": [b.to_student_dict() for b in self.teaching_blocks],
            "tasks": [t.to_student_dict() for t in self.tasks],
        }


def mission_produces_evidence(mission: SpeakingEducationalMission) -> bool:
    """A mission collects speaking evidence only when its intent is not `none`."""
    return mission.evidence_intent is not SpeakingEvidenceIntent.none


def is_teaching_only(mission: SpeakingEducationalMission) -> bool:
    """Teaching/review-only missions carry no evidence intent and no executable task."""
    return (
        mission.evidence_intent is SpeakingEvidenceIntent.none
        and mission.is_content_only
        and mission.execution_mode in (SpeakingExecutionMode.study, SpeakingExecutionMode.review)
    )
