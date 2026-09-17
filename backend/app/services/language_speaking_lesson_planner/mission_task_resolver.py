"""Canonical runtime resolution: legacy activity → educational mission → executable task (S11).

Callers must not manually scan ``blueprint.educational_missions``. This is the single
resolution boundary. When the current legacy activity has no matching executable
task, a typed non-task resolution is returned — identity is never invented.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_speaking_lesson_planner.mission_types import SpeakingMissionOutcome
from app.services.language_speaking_lesson_planner.planner import MISSION_LEGACY_ACTIVITY
from app.services.language_speaking_lesson_planner.types import (
    SpeakingLearningSession,
    SpeakingLessonBlueprint,
    SpeakingSessionActivityKind,
)


@dataclass(frozen=True, slots=True)
class SpeakingRuntimeTaskResolution:
    """Canonical resolution of the current executable cursor into mission/task identity.

    ``is_task=False`` means the current legacy activity is content/non-executable —
    callers must not invent a task_id.
    """

    is_task: bool
    mission_id: str = ""
    mission_kind: str = ""
    task_id: str = ""
    execution_mode: str = ""
    evidence_intent: str = ""
    target_skill_ids: tuple[str, ...] = ()
    retry_policy: str = SpeakingMissionOutcome.proceed.value
    legacy_activity_ref: str = ""
    activity_id: str = ""
    activity_kind: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "is_task": self.is_task,
            "mission_id": self.mission_id,
            "mission_kind": self.mission_kind,
            "task_id": self.task_id,
            "execution_mode": self.execution_mode,
            "evidence_intent": self.evidence_intent,
            "target_skill_ids": list(self.target_skill_ids),
            "retry_policy": self.retry_policy,
            "legacy_activity_ref": self.legacy_activity_ref,
            "activity_id": self.activity_id,
            "activity_kind": self.activity_kind,
            "reason": self.reason,
        }


def _activity_kind_for_id(
    blueprint: SpeakingLessonBlueprint,
    activity_id: str,
) -> SpeakingSessionActivityKind | None:
    for act in blueprint.activities:
        if act.activity_id == activity_id:
            return act.kind
    return None


def _non_task(
    *,
    activity_id: str,
    activity_kind: str = "",
    reason: str,
) -> SpeakingRuntimeTaskResolution:
    return SpeakingRuntimeTaskResolution(
        is_task=False,
        activity_id=activity_id,
        activity_kind=activity_kind,
        reason=reason,
    )


def resolve_activity_to_task(
    blueprint: SpeakingLessonBlueprint,
    activity_id: str,
) -> SpeakingRuntimeTaskResolution:
    """Resolve a legacy activity id to an executable mission task when one exists."""
    if not activity_id:
        return _non_task(activity_id="", reason="empty_activity_id")

    activity_kind = _activity_kind_for_id(blueprint, activity_id)
    kind_value = activity_kind.value if activity_kind else ""

    # Primary: exact legacy_activity_ref match on an executable task.
    for mission in blueprint.educational_missions:
        for task in mission.tasks:
            if task.legacy_activity_ref == activity_id:
                return SpeakingRuntimeTaskResolution(
                    is_task=True,
                    mission_id=mission.mission_id,
                    mission_kind=mission.mission_kind.value,
                    task_id=task.task_id,
                    execution_mode=task.execution_mode.value,
                    evidence_intent=task.evidence_intent.value,
                    target_skill_ids=task.target_skill_ids or mission.target_skill_ids,
                    retry_policy=mission.retry_policy.value,
                    legacy_activity_ref=task.legacy_activity_ref,
                    activity_id=activity_id,
                    activity_kind=kind_value,
                    reason="legacy_activity_ref_match",
                )

    # Fallback: mission kind ↔ activity kind mapping (planning-time bridge).
    if activity_kind is not None:
        for mission_kind, bridged_kind in MISSION_LEGACY_ACTIVITY.items():
            if bridged_kind is not activity_kind:
                continue
            for mission in blueprint.educational_missions:
                if mission.mission_kind is not mission_kind:
                    continue
                if not mission.tasks:
                    return _non_task(
                        activity_id=activity_id,
                        activity_kind=kind_value,
                        reason="mission_bridged_but_no_executable_task",
                    )
                task = mission.tasks[0]
                return SpeakingRuntimeTaskResolution(
                    is_task=True,
                    mission_id=mission.mission_id,
                    mission_kind=mission.mission_kind.value,
                    task_id=task.task_id,
                    execution_mode=task.execution_mode.value,
                    evidence_intent=task.evidence_intent.value,
                    target_skill_ids=task.target_skill_ids or mission.target_skill_ids,
                    retry_policy=mission.retry_policy.value,
                    legacy_activity_ref=task.legacy_activity_ref or activity_id,
                    activity_id=activity_id,
                    activity_kind=kind_value,
                    reason="mission_kind_activity_kind_bridge",
                )

    return _non_task(
        activity_id=activity_id,
        activity_kind=kind_value,
        reason="no_matching_executable_task",
    )


def resolve_current_task(
    blueprint: SpeakingLessonBlueprint,
    session: SpeakingLearningSession,
) -> SpeakingRuntimeTaskResolution:
    """Resolve the session's current legacy activity cursor to a mission/task."""
    return resolve_activity_to_task(blueprint, session.current_activity_id)
