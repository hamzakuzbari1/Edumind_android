"""Assemble student speaking journey bundle (S9 + S11 attempt + S12 read model)."""

from __future__ import annotations

from app.services.language_speaking.enums import SpeakingExecutionMode
from app.services.language_speaking_journey.read_model import (
    build_speaking_journey_read_model,
    student_safe_execution_mode,
)
from app.services.language_speaking_journey.types import (
    LANGUAGE_SPEAKING_JOURNEY_VERSION,
    SpeakingJourneyBundle,
    SpeakingJourneyMissionOut,
    SpeakingJourneyStepOut,
)
from app.services.language_speaking_knowledge_model.types import StudentSpeakingKnowledgeModel
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    SpeakingSessionAttemptLineage,
    student_safe_attempt_projection,
)
from app.services.language_speaking_lesson_planner.mission_task_resolver import resolve_current_task
from app.services.language_speaking_lesson_planner.storage import SpeakingStoredJourneyState
from app.services.language_speaking_lesson_planner.types import (
    SpeakingLearningPlan,
    SpeakingLearningSession,
    SpeakingLessonBlueprint,
    SpeakingSessionPhase,
)


def build_speaking_journey_bundle(
    *,
    official_level: str,
    plan: SpeakingLearningPlan | None,
    blueprint: SpeakingLessonBlueprint | None,
    session: SpeakingLearningSession | None,
    attempt_lineage: SpeakingSessionAttemptLineage | None = None,
    knowledge_model: StudentSpeakingKnowledgeModel | None = None,
    alex_daily_remaining_seconds: int | None = None,
    learning_stage_speaking: int | None = None,
    promotion_readiness: dict[str, object] | None = None,
) -> SpeakingJourneyBundle:
    focus_label = plan.primary_target_label if plan else "Speaking foundations"
    focus_reason = plan.selection_reason if plan else "Getting started"
    session_goal = blueprint.session_goal if blueprint else "Build your speaking confidence step by step"
    plan_summary = blueprint.reason_detail if blueprint else "Complete a placement or start your first session."

    steps: list[SpeakingJourneyStepOut] = []
    if blueprint:
        completed = set(session.completed_activity_ids if session else [])
        for act in blueprint.activities:
            if session and session.phase == SpeakingSessionPhase.completed:
                status = "done"
            elif act.activity_id in completed:
                status = "done"
            elif session and act.activity_id == session.current_activity_id:
                status = "active"
            else:
                status = "upcoming"
            steps.append(
                SpeakingJourneyStepOut(
                    step_id=act.activity_id,
                    label=act.title,
                    status=status,
                    kind=act.kind.value,
                )
            )

    current_activity_title = ""
    current_activity_id = ""
    current_activity_instructions = ""
    current_activity_kind = ""
    live_execution_ready = False
    has_active = session is not None and session.phase != SpeakingSessionPhase.completed
    if blueprint and session and has_active:
        current_activity_id = session.current_activity_id or ""
        for act in blueprint.activities:
            if act.activity_id == session.current_activity_id:
                current_activity_title = act.title
                current_activity_instructions = act.learner_instructions
                current_activity_kind = act.kind.value
                break

    activities_total = len(steps)
    activities_completed = sum(1 for s in steps if s.status == "done")
    # Remaining includes the active activity (still to finish) plus upcoming ones.
    activities_remaining = sum(1 for s in steps if s.status in ("active", "upcoming"))

    today_missions: list[SpeakingJourneyMissionOut] = []
    if blueprint:
        for mission in sorted(blueprint.educational_missions, key=lambda m: m.order_index):
            today_missions.append(
                SpeakingJourneyMissionOut(
                    mission_id=mission.mission_id,
                    kind=mission.mission_kind.value,
                    execution_mode=student_safe_execution_mode(mission.execution_mode),
                    order_index=mission.order_index,
                    title=mission.title,
                    is_live=mission.execution_mode is SpeakingExecutionMode.live_evi_conversation,
                    is_executable=mission.is_executable,
                )
            )

    task_id = ""
    if blueprint and session and has_active:
        resolution = resolve_current_task(blueprint, session)
        if resolution.is_task:
            task_id = resolution.task_id
            live_execution_ready = (
                resolution.execution_mode == SpeakingExecutionMode.live_evi_conversation.value
            )
    attempt_proj = student_safe_attempt_projection(attempt_lineage, task_id=task_id)

    stored = SpeakingStoredJourneyState(
        plan=plan,
        blueprint=blueprint,
        session=session,
        attempt_lineage=attempt_lineage,
    )
    read_model = build_speaking_journey_read_model(
        official_cefr=official_level or "A2",
        state=stored,
        knowledge_model=knowledge_model,
        alex_daily_remaining_seconds=alex_daily_remaining_seconds,
        learning_stage_speaking=learning_stage_speaking,
        promotion_readiness=promotion_readiness,
    )

    return SpeakingJourneyBundle(
        version=LANGUAGE_SPEAKING_JOURNEY_VERSION,
        current_focus_label=focus_label,
        current_focus_reason=focus_reason.replace("_", " "),
        session_goal=session_goal,
        official_level=official_level or "A2",
        plan_summary=plan_summary,
        today_session_id=session.session_id if session else "",
        today_session_phase=session.phase.value if session else "",
        current_activity_title=current_activity_title,
        steps=tuple(steps),
        next_recommendation=session.next_recommendation_summary if session else "",
        has_active_session=has_active,
        practice_with_alex_available=True,
        today_missions=tuple(today_missions),
        current_attempt_number=int(attempt_proj["current_attempt_number"]),
        is_retry=bool(attempt_proj["is_retry"]),
        completed_task_attempt_count=int(attempt_proj["completed_task_attempt_count"]),
        current_activity_id=current_activity_id,
        current_activity_instructions=current_activity_instructions,
        live_execution_ready=live_execution_ready,
        lesson_title=session_goal,
        current_activity_kind=current_activity_kind,
        activities_total=activities_total,
        activities_completed=activities_completed,
        activities_remaining=activities_remaining,
        read_model=read_model.to_student_dict(),
    )
