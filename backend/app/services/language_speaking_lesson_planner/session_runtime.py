"""Speaking learning session orchestration (S9)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_lesson_planner.decision_rules import decide_session_outcome
from app.services.language_speaking_lesson_planner.types import (
    SpeakingLearningSession,
    SpeakingSessionActivityKind,
    SpeakingSessionDecision,
    SpeakingSessionPhase,
    SpeakingTurnAccumulation,
    SpeakingLessonBlueprint,
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _phase_for_activity(kind: SpeakingSessionActivityKind) -> SpeakingSessionPhase:
    mapping = {
        SpeakingSessionActivityKind.warmup: SpeakingSessionPhase.introduced,
        SpeakingSessionActivityKind.target_intro: SpeakingSessionPhase.introduced,
        SpeakingSessionActivityKind.guided_practice: SpeakingSessionPhase.guided_practice,
        SpeakingSessionActivityKind.communicative_task: SpeakingSessionPhase.communicative_task,
        SpeakingSessionActivityKind.focused_retry: SpeakingSessionPhase.focused_retry,
        SpeakingSessionActivityKind.remediation: SpeakingSessionPhase.remediation,
        SpeakingSessionActivityKind.reflection: SpeakingSessionPhase.evaluated,
    }
    return mapping.get(kind, SpeakingSessionPhase.planned)


def create_learning_session(
    blueprint: SpeakingLessonBlueprint,
    *,
    live_session_id: str | None = None,
) -> SpeakingLearningSession:
    first = blueprint.activities[0] if blueprint.activities else None
    now = _now_iso()
    return SpeakingLearningSession(
        session_id=f"sls-{uuid.uuid4().hex[:12]}",
        blueprint_id=blueprint.blueprint_id,
        phase=SpeakingSessionPhase.planned,
        session_mode=blueprint.session_mode,
        current_activity_id=first.activity_id if first else "",
        completed_activity_ids=[],
        live_session_id=live_session_id or f"live-{uuid.uuid4().hex[:12]}",
        turn_accumulations=[],
        communicative_turns_completed=0,
        started_at=now,
        updated_at=now,
    )


def advance_session_activity(
    session: SpeakingLearningSession,
    blueprint: SpeakingLessonBlueprint,
    *,
    completed_activity_id: str,
) -> SpeakingLearningSession:
    if completed_activity_id not in session.completed_activity_ids:
        session.completed_activity_ids.append(completed_activity_id)
    idx = next((i for i, a in enumerate(blueprint.activities) if a.activity_id == completed_activity_id), -1)
    if idx >= 0:
        session.phase = _phase_for_activity(blueprint.activities[idx].kind)
    next_idx = idx + 1
    if 0 <= next_idx < len(blueprint.activities):
        session.current_activity_id = blueprint.activities[next_idx].activity_id
        session.phase = SpeakingSessionPhase.planned if session.phase == SpeakingSessionPhase.planned else session.phase
    session.updated_at = _now_iso()
    return session


def record_session_turn(
    session: SpeakingLearningSession,
    *,
    live_turn_id: str,
    target_skill_id: str,
    performance: float,
    success: bool,
    source_dimension: str,
    mistake_tags: tuple[str, ...],
    mutation_applied: bool,
) -> SpeakingLearningSession:
    session.turn_accumulations.append(
        SpeakingTurnAccumulation(
            live_turn_id=live_turn_id,
            target_skill_id=target_skill_id,
            performance=performance,
            success=success,
            source_dimension=source_dimension,
            mistake_tags=mistake_tags,
            mutation_applied=mutation_applied,
        )
    )
    session.communicative_turns_completed += 1
    session.phase = SpeakingSessionPhase.communicative_task
    session.updated_at = _now_iso()
    return session


def evaluate_session_boundary(
    session: SpeakingLearningSession,
    blueprint: SpeakingLessonBlueprint,
) -> SpeakingSessionDecision:
    decision = decide_session_outcome(
        session,
        primary_target_skill_id=blueprint.primary_target_skill_id,
        selection_reason=blueprint.selection_reason,
        min_communicative_turns=blueprint.min_communicative_turns,
    )
    session.phase = decision.next_phase
    session.outcome_kind = decision.outcome_kind
    session.outcome_detail = decision.detail
    session.next_recommendation_summary = decision.student_summary
    session.updated_at = _now_iso()
    return decision


def student_safe_activity(blueprint: SpeakingLessonBlueprint, activity_id: str) -> dict[str, object] | None:
    for act in blueprint.activities:
        if act.activity_id == activity_id:
            node = SPEAKING_SKILL_GRAPH.node_by_id(blueprint.primary_target_skill_id)
            return {
                "activity_id": act.activity_id,
                "kind": act.kind.value,
                "title": act.title,
                "learner_instructions": act.learner_instructions,
                "target_label": node.label if node else act.title,
                "completion_criteria": list(act.completion_criteria),
            }
    return None
