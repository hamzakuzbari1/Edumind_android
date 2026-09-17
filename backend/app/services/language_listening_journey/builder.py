"""Assemble canonical ListeningJourneyBundle (Phase 2.3)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.language_listening_bundles import (
    ActiveLessonPointerOut,
    HistoryEventOut,
    JourneyNarrativeOut,
    JourneyPromotionOut,
    JourneyTargetOut,
    ListeningJourneyBundleOut,
    ListeningJourneyMetaOut,
    PersonalGoalOut,
    TimelineStepOut,
)
from app.services.language_learning_facts.journey_assembler import (
    assemble_journey_facts,
    resolve_personal_goal_from_memory,
)
from app.services.language_learning_stage.storage import load_listening_stage
from app.services.language_learning_stage.types import stage_label
from app.services.language_learning_narrative.journey_builder import build_journey_narrative
from app.services.language_listening_journey import BUILDER_VERSION
from app.services.language_listening_reservation import listening_session_reservation_service
from app.services.language_listening_service import (
    _current_listening_grammar_id,
    _is_current_personalized_listening_item,
    _official_listening_cefr,
    _target_listening_cefr,
)
from app.services.language_learner_memory_service import get_memory
from app.services.language_promotion_readiness import evaluate_listening_promotion_readiness
from app.services.language_promotion_stability import evaluate_listening_promotion_stability
from app.services.language_promotion_test import check_promotion_test_eligibility
from app.services.language_promotion_test.storage import load_promotion_test_state
from app.services.language_promotion_test.session import find_active_session
from app.services.language_subscription_service import get_default_language


def _journey_narrative_out(narrative) -> JourneyNarrativeOut:
    return JourneyNarrativeOut(
        journey_headline=narrative.journey_headline,
        current_step_label=narrative.current_step_label,
        promotion_progress_message=narrative.promotion_progress_message,
        unlock_checklist=list(narrative.unlock_checklist),
        timeline_steps=[
            TimelineStepOut(
                key=s.key,
                label=s.label,
                done=s.done,
                active=s.active,
                current=s.current,
            )
            for s in narrative.timeline_steps
        ],
        history_events=[
            HistoryEventOut(period=e.period, text=e.text) for e in narrative.history_events
        ],
    )


async def build_listening_journey_bundle(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int | None = None,
) -> ListeningJourneyBundleOut:
    """Journey-scoped bundle — no lesson playback."""
    lid = language_id
    if lid is None:
        language = await get_default_language(db)
        lid = language.id

    official = await _official_listening_cefr(db, student_id=student_id, language_id=lid)
    target = await _target_listening_cefr(db, student_id=student_id, language_id=lid)
    learning_stage = await load_listening_stage(db, student_id=student_id, language_id=lid)
    readiness = await evaluate_listening_promotion_readiness(
        db, student_id=student_id, language_id=lid, official_cefr=official
    )
    stability = await evaluate_listening_promotion_stability(
        db, student_id=student_id, language_id=lid
    )
    eligibility = await check_promotion_test_eligibility(
        db, student_id=student_id, language_id=lid
    )
    memory = await get_memory(db, student_id=student_id, language_id=lid)
    personal_goal = resolve_personal_goal_from_memory(
        learning_goals=memory.get("learning_goals") if memory else None,
        future_goal=memory.get("future_goal") if memory else None,
    )

    active_id = await listening_session_reservation_service.load_reserved_content_id(
        db, student_id=student_id, language_id=lid
    )
    active_lifecycle = None
    if active_id is not None:
        from app.models.language.content import LanguageContentItem
        from app.services.language_listening_reservation.storage import load_reservation_by_content

        active_item = await db.get(LanguageContentItem, active_id)
        grammar_id = await _current_listening_grammar_id(db, student_id=student_id, language_id=lid)
        if not _is_current_personalized_listening_item(
            active_item, student_id=student_id, grammar_id=grammar_id
        ):
            await listening_session_reservation_service.skip_reservation(
                db, student_id=student_id, language_id=lid, content_item_id=active_id
            )
            active_id = None

    if active_id is not None:
        reservation = await load_reservation_by_content(
            db, student_id=student_id, language_id=lid, content_item_id=active_id
        )
        if reservation is not None:
            active_lifecycle = str(reservation.lifecycle_state)

    state = await load_promotion_test_state(db, student_id=student_id, language_id=lid)
    attempts = state.get("attempts") or []
    last_attempt_raw = attempts[-1] if attempts else None
    last_result = None
    last_target = None
    last_official = None
    latest_rec = None
    if isinstance(last_attempt_raw, dict):
        last_result = str(last_attempt_raw.get("result") or "") or None
        last_target = str(last_attempt_raw.get("target_cefr") or "") or None
        last_official = str(last_attempt_raw.get("official_cefr") or "") or None
        latest_rec = str(last_attempt_raw.get("recommendation") or "") or None

    active_session = await find_active_session(db, student_id=student_id, language_id=lid)

    facts = assemble_journey_facts(
        official_level=official or "A1",
        personal_goal=personal_goal,
        readiness=readiness,
        stability=stability,
        eligibility_can_start=eligibility.eligible,
        target_cefr=target or eligibility.target_cefr,
        active_lesson_id=active_id,
        active_lifecycle=active_lifecycle,
        last_attempt_result=last_result,
        last_attempt_target_cefr=last_target,
        last_attempt_official_cefr=last_official,
        latest_recommendation=latest_rec,
        has_active_test_session=active_session is not None,
    )
    narrative = build_journey_narrative(facts)

    return ListeningJourneyBundleOut(
        official_level=facts.official_level,
        learning_stage=learning_stage,
        learning_stage_label=stage_label(official_cefr=facts.official_level, stage=learning_stage),
        journey_target=JourneyTargetOut(
            level=facts.journey_target.level,
            label=facts.journey_target.label,
        ),
        personal_goal=PersonalGoalOut(
            id=facts.personal_goal.personal_goal_id,
            label=facts.personal_goal.personal_goal_label,
        ),
        narrative=_journey_narrative_out(narrative),
        promotion=JourneyPromotionOut(
            readiness_band=facts.promotion.readiness_band,
            can_start_test=facts.promotion.can_start_test,
            estimated_lessons_remaining=facts.promotion.estimated_lessons_remaining,
            primary_blockers=list(facts.promotion.primary_blockers),
        ),
        active_lesson=ActiveLessonPointerOut(
            lesson_id=facts.active_lesson.lesson_id,
            lifecycle_state=facts.active_lesson.lifecycle_state,  # type: ignore[arg-type]
        ),
        meta=ListeningJourneyMetaOut(builder_version=BUILDER_VERSION),
    )
