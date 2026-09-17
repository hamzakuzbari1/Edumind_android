"""Persistence for S9 speaking learning plan and session (JSONB bucket).

S11 extends the bucket with durable attempt lineage under ``attempt_lineage``.
S12 replaces the fragile 4-tuple load contract with ``SpeakingStoredJourneyState``.
No migration — lineage rides ``promotion_readiness_json[speaking]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.language_speaking_knowledge_model.storage import SPEAKING_BUCKET_KEY
from app.services.language_speaking_lesson_planner.types import (
    SpeakingLearningPlan,
    SpeakingLearningSession,
    SpeakingLessonBlueprint,
    SpeakingSessionActivityKind,
    SpeakingSessionMode,
    SpeakingSessionOutcomeKind,
    SpeakingSessionPhase,
    SpeakingTurnAccumulation,
)
LEARNING_PLAN_KEY = "learning_plan"
LEARNING_SESSION_KEY = "learning_session"
ACTIVE_BLUEPRINT_KEY = "active_blueprint"
ATTEMPT_LINEAGE_KEY = "attempt_lineage"

def speaking_bucket_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    raw = payload.get(SPEAKING_BUCKET_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def merge_speaking_bucket_into_payload(
    payload: dict[str, Any] | None,
    speaking_bucket: dict[str, Any],
) -> dict[str, Any]:
    out = dict(payload) if isinstance(payload, dict) else {}
    out[SPEAKING_BUCKET_KEY] = speaking_bucket
    return out


def _educational_missions_from_raw(raw: Any) -> tuple:
    """Deserialize S10.1 educational missions.

    Construction validates every mission triple via the dataclass invariant
    (`validate_mission_combination`), so persisted illegal contracts fail deterministically.
    """
    from app.services.language_speaking.enums import (
        SpeakingEvidenceIntent,
        SpeakingExecutionMode,
        SpeakingMissionKind,
        SpeakingTeachingBlockKind,
    )
    from app.services.language_speaking_lesson_planner.mission_types import (
        SpeakingEducationalMission,
        SpeakingExecutableTask,
        SpeakingLearningObjective,
        SpeakingMissionOutcome,
        SpeakingTeachingBlock,
    )

    if not isinstance(raw, list):
        return ()
    missions: list[SpeakingEducationalMission] = []
    for m in raw:
        if not isinstance(m, dict) or not m.get("mission_id"):
            continue
        objectives: list[SpeakingLearningObjective] = []
        for o in m.get("objectives") or []:
            if not isinstance(o, dict):
                continue
            objectives.append(
                SpeakingLearningObjective(
                    objective_id=str(o.get("objective_id", "")),
                    target_skill_id=str(o.get("target_skill_id", "")),
                    student_objective_text=str(o.get("student_objective_text", "")),
                    expected_outcome=str(o.get("expected_outcome", "")),
                    evidence_expectation=SpeakingEvidenceIntent(str(o.get("evidence_expectation", "none"))),
                    prerequisite_skill_ids=tuple(str(x) for x in (o.get("prerequisite_skill_ids") or [])),
                )
            )
        blocks: list[SpeakingTeachingBlock] = []
        for b in m.get("teaching_blocks") or []:
            if not isinstance(b, dict):
                continue
            blocks.append(
                SpeakingTeachingBlock(
                    block_id=str(b.get("block_id", "")),
                    kind=SpeakingTeachingBlockKind(str(b.get("kind", "explanation"))),
                    title=str(b.get("title", "")),
                    body=str(b.get("body", "")),
                    target_skill_ids=tuple(str(x) for x in (b.get("target_skill_ids") or [])),
                    is_evidence=bool(b.get("is_evidence", False)),
                )
            )
        tasks: list[SpeakingExecutableTask] = []
        for t in m.get("tasks") or []:
            if not isinstance(t, dict):
                continue
            tasks.append(
                SpeakingExecutableTask(
                    task_id=str(t.get("task_id", "")),
                    execution_mode=SpeakingExecutionMode(str(t.get("execution_mode", "study"))),
                    evidence_intent=SpeakingEvidenceIntent(str(t.get("evidence_intent", "none"))),
                    prompt=str(t.get("prompt", "")),
                    target_skill_ids=tuple(str(x) for x in (t.get("target_skill_ids") or [])),
                    context_descriptor=str(t.get("context_descriptor", "")),
                    legacy_activity_ref=str(t.get("legacy_activity_ref", "")),
                )
            )
        missions.append(
            SpeakingEducationalMission(
                mission_id=str(m["mission_id"]),
                mission_kind=SpeakingMissionKind(str(m.get("mission_kind", "teaching"))),
                execution_mode=SpeakingExecutionMode(str(m.get("execution_mode", "study"))),
                evidence_intent=SpeakingEvidenceIntent(str(m.get("evidence_intent", "none"))),
                order_index=int(m.get("order_index", 0)),
                title=str(m.get("title", "")),
                learner_instructions=str(m.get("learner_instructions", "")),
                objectives=tuple(objectives),
                target_skill_ids=tuple(str(x) for x in (m.get("target_skill_ids") or [])),
                teaching_blocks=tuple(blocks),
                tasks=tuple(tasks),
                retry_policy=SpeakingMissionOutcome(str(m.get("retry_policy", "continue"))),
            )
        )
    return tuple(missions)


def blueprint_from_dict(raw: dict[str, Any] | None) -> SpeakingLessonBlueprint | None:
    if not isinstance(raw, dict) or not raw.get("blueprint_id"):
        return None
    from app.services.language_speaking_lesson_planner.types import AlexTutoringContext, SpeakingSessionActivity

    alex_raw = raw.get("alex_context") or {}
    activities_raw = raw.get("activities") or []
    activities: list[SpeakingSessionActivity] = []
    if isinstance(activities_raw, list):
        for a in activities_raw:
            if not isinstance(a, dict):
                continue
            activities.append(
                SpeakingSessionActivity(
                    activity_id=str(a.get("activity_id", "")),
                    kind=SpeakingSessionActivityKind(str(a.get("kind", "warmup"))),
                    title=str(a.get("title", "")),
                    learner_instructions=str(a.get("learner_instructions", "")),
                    target_skill_ids=tuple(str(x) for x in (a.get("target_skill_ids") or [])),
                    completion_criteria=tuple(str(x) for x in (a.get("completion_criteria") or [])),
                    optional_render_hints=tuple(str(x) for x in (a.get("optional_render_hints") or [])),
                )
            )
    alex = AlexTutoringContext(
        session_goal=str(alex_raw.get("session_goal", "")),
        target_skill_label=str(alex_raw.get("target_skill_label", "")),
        communicative_scenario=str(alex_raw.get("communicative_scenario", "")),
        encourage_behaviors=tuple(str(x) for x in (alex_raw.get("encourage_behaviors") or [])),
        elicit_behaviors=tuple(str(x) for x in (alex_raw.get("elicit_behaviors") or [])),
        retry_focus=str(alex_raw.get("retry_focus", "")),
        conversation_constraints=tuple(str(x) for x in (alex_raw.get("conversation_constraints") or [])),
    )
    return SpeakingLessonBlueprint(
        blueprint_id=str(raw["blueprint_id"]),
        blueprint_version=str(raw.get("blueprint_version", "9.0.0")),
        schema_version=str(raw.get("schema_version", "9.0.0")),
        compatibility_notes=tuple(str(x) for x in (raw.get("compatibility_notes") or [])),
        blueprint_hash=str(raw.get("blueprint_hash", "")),
        recommendation_id=str(raw.get("recommendation_id", "")),
        session_goal=str(raw.get("session_goal", "")),
        target_skill_ids=tuple(str(x) for x in (raw.get("target_skill_ids") or [])),
        primary_target_skill_id=str(raw.get("primary_target_skill_id", "")),
        selection_reason=str(raw.get("selection_reason", "")),
        reason_detail=str(raw.get("reason_detail", "")),
        evidence_basis=tuple(str(x) for x in (raw.get("evidence_basis") or [])),
        session_mode=SpeakingSessionMode(str(raw.get("session_mode", "standard"))),
        official_cefr_hint=str(raw.get("official_cefr_hint", "A2")),
        speaking_goal=str(raw.get("speaking_goal", "general_english")),
        activities=tuple(activities),
        alex_context=alex,
        completion_evidence_requirements=tuple(str(x) for x in (raw.get("completion_evidence_requirements") or [])),
        remediation_strategy=str(raw.get("remediation_strategy", "")),
        retry_strategy=str(raw.get("retry_strategy", "")),
        min_communicative_turns=int(raw.get("min_communicative_turns", 2)),
        educational_missions=_educational_missions_from_raw(raw.get("educational_missions")),
    )


def plan_from_dict(raw: dict[str, Any] | None) -> SpeakingLearningPlan | None:
    if not isinstance(raw, dict) or not raw.get("plan_id"):
        return None
    return SpeakingLearningPlan(
        plan_id=str(raw["plan_id"]),
        active_blueprint_id=str(raw.get("active_blueprint_id", "")),
        primary_target_skill_id=str(raw.get("primary_target_skill_id", "")),
        primary_target_label=str(raw.get("primary_target_label", "")),
        selection_reason=str(raw.get("selection_reason", "")),
        updated_at=str(raw.get("updated_at", "")),
    )


def session_from_dict(raw: dict[str, Any] | None) -> SpeakingLearningSession | None:
    if not isinstance(raw, dict) or not raw.get("session_id"):
        return None
    turns_raw = raw.get("turn_accumulations") or []
    turns: list[SpeakingTurnAccumulation] = []
    if isinstance(turns_raw, list):
        for t in turns_raw:
            if not isinstance(t, dict):
                continue
            turns.append(
                SpeakingTurnAccumulation(
                    live_turn_id=str(t.get("live_turn_id", "")),
                    target_skill_id=str(t.get("target_skill_id", "")),
                    performance=float(t.get("performance", 0.0)),
                    success=bool(t.get("success", False)),
                    source_dimension=str(t.get("source_dimension", "")),
                    mistake_tags=tuple(str(x) for x in (t.get("mistake_tags") or [])),
                    mutation_applied=bool(t.get("mutation_applied", False)),
                )
            )
    outcome_raw = raw.get("outcome_kind")
    outcome = SpeakingSessionOutcomeKind(outcome_raw) if outcome_raw else None
    return SpeakingLearningSession(
        session_id=str(raw["session_id"]),
        blueprint_id=str(raw.get("blueprint_id", "")),
        phase=SpeakingSessionPhase(str(raw.get("phase", "planned"))),
        session_mode=SpeakingSessionMode(str(raw.get("session_mode", "standard"))),
        current_activity_id=str(raw.get("current_activity_id", "")),
        completed_activity_ids=[str(x) for x in (raw.get("completed_activity_ids") or [])],
        live_session_id=str(raw.get("live_session_id", "")),
        turn_accumulations=turns,
        communicative_turns_completed=int(raw.get("communicative_turns_completed", 0)),
        started_at=str(raw.get("started_at", "")),
        updated_at=str(raw.get("updated_at", "")),
        outcome_kind=outcome,
        outcome_detail=str(raw.get("outcome_detail", "")),
        next_recommendation_summary=str(raw.get("next_recommendation_summary", "")),
    )


def attempt_lineage_from_dict(raw: dict[str, Any] | None):
    from app.services.language_speaking_lesson_planner.attempt_lineage import (
        SpeakingSessionAttemptLineage,
    )

    return SpeakingSessionAttemptLineage.from_dict(raw)


@dataclass(frozen=True, slots=True)
class SpeakingStoredJourneyState:
    """Typed immutable S9 speaking state loaded from the JSONB speaking bucket (S12).

    Replaces the fragile 4-tuple return of ``load_s9_state``. Stored JSONB shape is
    unchanged — this is a load-time contract only. Future fields (budget, readiness)
    can be added as optional attributes without breaking callers.
    """

    plan: SpeakingLearningPlan | None = None
    blueprint: SpeakingLessonBlueprint | None = None
    session: SpeakingLearningSession | None = None
    attempt_lineage: Any = None


def load_s9_state(speaking_bucket: dict[str, Any] | None) -> SpeakingStoredJourneyState:
    """Load S9 state as a typed immutable object (no tuple unpacking)."""
    bucket = speaking_bucket if isinstance(speaking_bucket, dict) else {}
    return SpeakingStoredJourneyState(
        plan=plan_from_dict(bucket.get(LEARNING_PLAN_KEY)),
        blueprint=blueprint_from_dict(bucket.get(ACTIVE_BLUEPRINT_KEY)),
        session=session_from_dict(bucket.get(LEARNING_SESSION_KEY)),
        attempt_lineage=attempt_lineage_from_dict(bucket.get(ATTEMPT_LINEAGE_KEY)),
    )


def save_s9_state(
    speaking_bucket: dict[str, Any] | None,
    *,
    plan: SpeakingLearningPlan | None = None,
    blueprint: SpeakingLessonBlueprint | None = None,
    session: SpeakingLearningSession | None = None,
    attempt_lineage: Any = None,
) -> dict[str, Any]:
    bucket = dict(speaking_bucket) if isinstance(speaking_bucket, dict) else {}
    if plan is not None:
        bucket[LEARNING_PLAN_KEY] = plan.to_dict()
    if blueprint is not None:
        bucket[ACTIVE_BLUEPRINT_KEY] = blueprint.to_dict()
    if session is not None:
        bucket[LEARNING_SESSION_KEY] = session.to_dict()
    if attempt_lineage is not None:
        bucket[ATTEMPT_LINEAGE_KEY] = attempt_lineage.to_dict()
    return bucket
