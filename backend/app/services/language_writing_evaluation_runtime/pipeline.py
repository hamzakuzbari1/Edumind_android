"""Evaluation & revision pipeline (W7) — hybrid evaluation + render-only downstream."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.language_writing.enums import WritingCoachPersonality, WritingLessonLifecycle, WritingRevisionStatus
from app.services.language_writing_curriculum.goal_profiles import profile_for_goal
from app.services.language_writing_coach.adaptive_tone import AdaptiveToneContext, AdaptiveToneTrigger
from app.services.language_writing_coach.priority import select_educational_priority
from app.services.language_writing_coach.renderer import render_revision_plan
from app.services.language_writing_coach.revision_plan import revision_plan_to_feedback
from app.services.language_writing_coach.types import CoachInputBundle, CoachNarrativeContext
from app.services.language_writing_evaluator.blueprint_snapshot import EvaluatorBlueprintSnapshot, blueprint_snapshot_from_dict
from app.services.language_writing_evaluator.engine import evaluate_writing_draft, word_count
from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult
from app.services.language_writing_evaluator.facts_deserialize import evaluation_result_from_dict
from app.services.language_writing_explainability.facts_assembler import assemble_writing_facts
from app.services.language_writing_explainability.writing_narrative import build_writing_learning_narrative
from app.services.language_writing_generation import WRITING_BLUEPRINT_KEY, WRITING_CURRICULUM_KEY, WRITING_GENERATION_KEY
from app.services.language_writing_revision.persistence import (
    WRITING_EVALUATION_FACTS_KEY,
    load_revision_session,
    new_draft_id,
    new_revision_id,
    persist_revision_turn,
)
from app.services.language_writing_revision.types import WritingDraft, WritingRevision, WritingRevisionSession
from app.services.language_writing_evaluation_runtime.types import EvaluationRevisionTurnResult


def _generation_hash(body_json: dict[str, object]) -> str:
    gen = body_json.get(WRITING_GENERATION_KEY) or {}
    if isinstance(gen, dict):
        return str(gen.get("generation_hash") or "")
    canonical = body_json.get("canonical_lesson") or {}
    if isinstance(canonical, dict):
        return str(canonical.get("generation_hash") or "")
    return ""


def _blueprint_snapshot(body_json: dict[str, object]) -> EvaluatorBlueprintSnapshot:
    bp = body_json.get(WRITING_BLUEPRINT_KEY) or {}
    if not isinstance(bp, dict):
        raise ValueError("Lesson blueprint missing from content item")
    return blueprint_snapshot_from_dict(bp, generation_hash=_generation_hash(body_json))


def _official_cefr(body_json: dict[str, object]) -> str:
    curriculum = body_json.get(WRITING_CURRICULUM_KEY) or {}
    blueprint = body_json.get(WRITING_BLUEPRINT_KEY) or {}
    if isinstance(curriculum, dict) and curriculum.get("official_cefr"):
        return str(curriculum.get("official_cefr"))
    if isinstance(blueprint, dict) and blueprint.get("official_cefr"):
        return str(blueprint.get("official_cefr"))
    return "B1"


def _writing_prompt(body_json: dict[str, object]) -> str:
    canonical = body_json.get("canonical_lesson") or {}
    if isinstance(canonical, dict):
        return str(canonical.get("writing_prompt") or canonical.get("instructions") or "")
    gen = body_json.get(WRITING_GENERATION_KEY) or {}
    if isinstance(gen, dict):
        return str(gen.get("writing_prompt") or "")
    return ""


async def process_writing_draft_turn(
    *,
    student_id: int,
    content_item_id: int,
    draft_text: str,
    body_json: dict[str, object],
    personality: WritingCoachPersonality | None = None,
    force_complete: bool = False,
) -> tuple[EvaluationRevisionTurnResult, dict[str, object]]:
    """Run hybrid evaluation → render-only narrative/coach → persist."""
    blueprint = _blueprint_snapshot(body_json)
    official_cefr = _official_cefr(body_json)
    session = load_revision_session(body_json) or WritingRevisionSession(
        student_id=student_id,
        content_item_id=content_item_id,
        lifecycle=WritingLessonLifecycle.drafting,
    )

    attempt = len(session.drafts) + 1
    draft_id = new_draft_id(content_item_id, attempt)
    draft = WritingDraft(
        draft_id=draft_id,
        attempt_number=attempt,
        text=draft_text.strip(),
        word_count=word_count(draft_text),
        submitted_at=datetime.now(timezone.utc).isoformat(),
        revision_status=WritingRevisionStatus.pending_coach,
    )
    session.drafts.append(draft)
    if session.first_draft_id is None:
        session.first_draft_id = draft_id

    previous: WritingEvaluationEngineResult | None = None
    if attempt > 1:
        prev_raw = body_json.get(WRITING_EVALUATION_FACTS_KEY)
        if isinstance(prev_raw, dict):
            previous = evaluation_result_from_dict(prev_raw)

    evaluation = await evaluate_writing_draft(
        draft.text,
        draft_id=draft_id,
        revision_number=attempt,
        blueprint=blueprint,
        official_cefr=official_cefr,
        previous=previous,
        writing_prompt=_writing_prompt(body_json),
    )

    facts_bundle = assemble_writing_facts(
        blueprint=blueprint,
        evaluation=evaluation,
        lifecycle=session.lifecycle,
        official_cefr=official_cefr,
    )
    narrative = build_writing_learning_narrative(facts_bundle, evaluation)

    goal_profile = profile_for_goal(facts_bundle.lesson.goal)
    coach_personality = personality or goal_profile.coach_defaults.personality
    tone = AdaptiveToneContext.resolve(
        personality=coach_personality,
        triggers=(AdaptiveToneTrigger.recent_improvement,) if attempt > 1 else (),
    )

    what_improved = evaluation.comparison.improved if evaluation.comparison else ()

    # ONE canonical educational priority — chosen once, rendered by the coach only.
    educational_priority = select_educational_priority(
        evaluation=evaluation,
        goal_label=goal_profile.label,
    )

    coach_input = CoachInputBundle(
        evaluation=evaluation.to_coach_evaluation(),
        goal_profile=goal_profile,
        narrative_coach_summary=narrative.coach_summary,
        learning_outcomes=blueprint.learning_outcomes,
        node_common_mistakes=blueprint.common_mistakes,
    )
    coach_narrative = CoachNarrativeContext(
        coach_summary=narrative.coach_summary,
        focus_sentence=narrative.focus_sentence,
        improvement_context=narrative.improvement_context,
        strengths_summary=narrative.strengths_summary,
        priority_area=narrative.priority_area,
    )
    revision_plan = render_revision_plan(
        coach_input,
        coach_narrative,
        evaluation=evaluation,
        priority=educational_priority,
        personality=coach_personality,
        revision_turn=attempt,
        tone=tone,
        what_improved=what_improved,
    )

    completed = force_complete and evaluation.revision_readiness.ready

    revision = WritingRevision(
        revision_id=new_revision_id(content_item_id, attempt),
        from_draft_id=draft_id,
        to_draft_id=None,
        feedback=revision_plan_to_feedback(revision_plan),
        revision_plan=revision_plan,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    session.revisions.append(revision)

    if completed:
        session.lifecycle = WritingLessonLifecycle.completed
        session.final_draft_id = draft_id
        session.completed_at = datetime.now(timezone.utc).isoformat()
    else:
        session.lifecycle = WritingLessonLifecycle.revising

    updated_body = persist_revision_turn(
        body_json,
        session=session,
        evaluation=evaluation,
        revision_plan=revision_plan,
    )

    return (
        EvaluationRevisionTurnResult(
            success=True,
            session=session,
            evaluation=evaluation,
            narrative=narrative,
            revision_plan=revision_plan,
            completed=completed,
            revision_number=attempt,
        ),
        updated_body,
    )


def process_writing_draft_turn_sync(
    *,
    student_id: int,
    content_item_id: int,
    draft_text: str,
    body_json: dict[str, object],
    personality: WritingCoachPersonality | None = None,
    force_complete: bool = False,
) -> tuple[EvaluationRevisionTurnResult, dict[str, object]]:
    """Sync wrapper for verification scripts."""
    import asyncio

    return asyncio.run(
        process_writing_draft_turn(
            student_id=student_id,
            content_item_id=content_item_id,
            draft_text=draft_text,
            body_json=body_json,
            personality=personality,
            force_complete=force_complete,
        )
    )
