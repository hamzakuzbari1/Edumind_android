"""Revision session persistence (W7) — drafts, facts, coach output, history."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.language_writing.enums import WritingLessonLifecycle, WritingRevisionStatus
from app.services.language_writing_coach.revision_plan import revision_plan_to_feedback
from app.services.language_writing_coach.types import WritingRevisionPlan
from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult
from app.services.language_writing_revision.types import WritingDraft, WritingRevision, WritingRevisionSession

WRITING_EVALUATION_FACTS_KEY = "writing_evaluation_facts"
WRITING_REVISION_SESSION_KEY = "writing_revision_session"
WRITING_COACH_PLAN_KEY = "writing_coach_plan"
WRITING_COMPLETION_KEY = "writing_completion"
PERSISTENCE_VERSION = "7.0.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_revision_session(body_json: dict[str, object] | None) -> WritingRevisionSession | None:
    raw = (body_json or {}).get(WRITING_REVISION_SESSION_KEY)
    if not isinstance(raw, dict):
        return None
    drafts = [
        WritingDraft(
            draft_id=str(d.get("draft_id") or ""),
            attempt_number=int(d.get("attempt_number") or 0),
            text=str(d.get("text") or ""),
            word_count=int(d.get("word_count") or 0),
            submitted_at=str(d.get("submitted_at") or ""),
            revision_status=WritingRevisionStatus(str(d.get("revision_status") or WritingRevisionStatus.pending_coach.value)),
        )
        for d in raw.get("drafts") or []
        if isinstance(d, dict)
    ]
    revisions: list[WritingRevision] = []
    for r in raw.get("revisions") or []:
        if not isinstance(r, dict):
            continue
        plan_raw = r.get("revision_plan")
        plan = None
        if isinstance(plan_raw, dict):
            from app.services.language_writing.enums import WritingCoachPersonality
            from app.services.language_writing_coach.types import WritingRevisionPlan

            plan = WritingRevisionPlan(
                encouragement=str(plan_raw.get("encouragement") or ""),
                main_issue=str(plan_raw.get("main_issue") or ""),
                priority_fix=str(plan_raw.get("priority_fix") or ""),
                concrete_example=str(plan_raw.get("concrete_example") or ""),
                revision_mission=str(plan_raw.get("revision_mission") or ""),
                ready_to_complete=bool(plan_raw.get("ready_to_complete")),
                next_lesson_recommendation=str(plan_raw.get("next_lesson_recommendation") or ""),
                what_improved=tuple(plan_raw.get("what_improved") or ()),
                personality=WritingCoachPersonality(str(plan_raw.get("personality") or WritingCoachPersonality.friendly_teacher.value)),
                revision_turn=int(plan_raw.get("revision_turn") or 1),
            )
        feedback = revision_plan_to_feedback(plan) if plan else None
        if feedback is None:
            continue
        revisions.append(
            WritingRevision(
                revision_id=str(r.get("revision_id") or ""),
                from_draft_id=str(r.get("from_draft_id") or ""),
                to_draft_id=str(r.get("to_draft_id")) if r.get("to_draft_id") else None,
                feedback=feedback,
                revision_plan=plan,
                created_at=str(r.get("created_at") or ""),
            )
        )
    lifecycle_raw = raw.get("lifecycle") or WritingLessonLifecycle.not_started.value
    return WritingRevisionSession(
        student_id=int(raw.get("student_id") or 0),
        content_item_id=int(raw.get("content_item_id") or 0),
        lifecycle=WritingLessonLifecycle(str(lifecycle_raw)),
        drafts=drafts,
        revisions=revisions,
        first_draft_id=str(raw.get("first_draft_id")) if raw.get("first_draft_id") else None,
        final_draft_id=str(raw.get("final_draft_id")) if raw.get("final_draft_id") else None,
        completed_at=str(raw.get("completed_at")) if raw.get("completed_at") else None,
    )


def persist_revision_turn(
    body_json: dict[str, object],
    *,
    session: WritingRevisionSession,
    evaluation: WritingEvaluationEngineResult,
    revision_plan: WritingRevisionPlan,
) -> dict[str, object]:
    """Merge revision session + canonical evaluation into content item body_json."""
    updated = dict(body_json or {})
    eval_dict = evaluation.to_persistence_dict()
    updated[WRITING_EVALUATION_FACTS_KEY] = eval_dict
    updated[WRITING_COACH_PLAN_KEY] = revision_plan.to_student_dict()
    updated[WRITING_COMPLETION_KEY] = evaluation.completion.to_persistence_dict()
    comparison = evaluation.comparison
    session_payload = {
        "student_id": session.student_id,
        "content_item_id": session.content_item_id,
        "lifecycle": session.lifecycle.value,
        "drafts": [
            {
                "draft_id": d.draft_id,
                "attempt_number": d.attempt_number,
                "text": d.text,
                "word_count": d.word_count,
                "submitted_at": d.submitted_at,
                "revision_status": d.revision_status.value,
            }
            for d in session.drafts
        ],
        "revisions": [
            {
                "revision_id": r.revision_id,
                "from_draft_id": r.from_draft_id,
                "to_draft_id": r.to_draft_id,
                "revision_plan": r.revision_plan.to_student_dict() if r.revision_plan else None,
                "created_at": r.created_at,
                "comparison": comparison.to_persistence_dict() if comparison else None,
            }
            for r in session.revisions
        ],
        "first_draft_id": session.first_draft_id,
        "final_draft_id": session.final_draft_id,
        "completed_at": session.completed_at,
        "persistence_version": PERSISTENCE_VERSION,
    }
    prior_session = body_json.get(WRITING_REVISION_SESSION_KEY) or {}
    history = list(prior_session.get("evaluation_facts_history") or []) if isinstance(prior_session, dict) else []
    history.append(eval_dict)
    session_payload["evaluation_facts_history"] = history[-10:]
    updated[WRITING_REVISION_SESSION_KEY] = session_payload
    return updated


def new_draft_id(content_item_id: int, attempt: int) -> str:
    return f"draft:{content_item_id}:{attempt}:{int(datetime.now(timezone.utc).timestamp())}"


def new_revision_id(content_item_id: int, turn: int) -> str:
    return f"revision:{content_item_id}:{turn}:{int(datetime.now(timezone.utc).timestamp())}"
