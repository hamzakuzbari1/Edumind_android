"""Build canonical LessonExperienceBundle from facts + narrative (Phase 2.3)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.models.language.reservation import LanguageListeningReservation
from app.schemas.language_learning import LessonProgressOut, LessonQuestionOut
from app.schemas.language_listening_bundles import (
    AfterLessonOut,
    LessonExperienceBundleOut,
    LessonExperienceMetaOut,
    LessonGoalOut,
    LessonNarrativeOut,
    LessonPlaybackOut,
    LessonType,
)
from app.services.language_content_service import lesson_body_for_student, resolve_listening_audio
from app.services.language_learning_facts.assembler import assemble_lesson_facts, assemble_progression_facts
from app.services.language_learning_facts.types import PostLessonFacts
from app.services.language_learning_goal import GOAL_KEY
from app.services.language_learning_goal.profiles import profile_for_goal
from app.services.language_learning_goal.types import LearningGoal
from app.services.language_learning_narrative.builder import build_after_lesson_narrative, build_lesson_narrative
from app.services.language_listening_explainability.facts import build_explainability_facts
from app.services.language_listening_explainability.signals import extract_signals
from app.services.language_listening_lesson_experience import BUILDER_VERSION, FACTS_SCHEMA_VERSION
from app.services.language_listening_lesson_experience.legacy_adapter import bundle_to_legacy_payload
from app.services.language_listening_service import _official_listening_cefr, _target_listening_cefr
from app.services.language_listening_curriculum.memory import CURRICULUM_KEY


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _resolve_lesson_goal_id(body: dict) -> str | None:
    goal_meta = _as_dict(body.get(GOAL_KEY))
    raw = str(goal_meta.get("learning_goal") or "").strip()
    if not raw:
        conf = _as_dict(body.get("listening_confidence_lesson"))
        raw = str(conf.get("learning_goal") or "").strip()
    if not raw:
        return None
    try:
        return LearningGoal(raw).value
    except ValueError:
        return raw


def _lesson_type_from_body(body: dict) -> LessonType:
    intent = str(_as_dict(body.get(CURRICULUM_KEY)).get("lesson_intent") or "").strip().lower()
    if intent == "review":
        return "review"
    if intent in ("promotion", "promotion_assessment"):
        return "promotion_assessment"
    if intent == "placement":
        return "placement"
    return "practice"


def _map_lifecycle(
    *,
    reservation: LanguageListeningReservation | None,
    progress_status: str | None,
    has_after_lesson: bool = False,
) -> str:
    if reservation is not None:
        state = str(reservation.lifecycle_state)
        if state in ("queued", "reserved", "started", "completed", "reviewed"):
            if has_after_lesson and state == "completed":
                return "reviewed"
            return state
    status = str(progress_status or "not_started")
    if has_after_lesson or status == "completed":
        return "reviewed" if has_after_lesson else "completed"
    if status == "in_progress":
        return "started"
    return "reserved" if reservation else "queued"


def _questions_out(body: dict) -> list[LessonQuestionOut]:
    out: list[LessonQuestionOut] = []
    for q in body.get("questions") or []:
        if not isinstance(q, dict):
            continue
        out.append(
            LessonQuestionOut(
                id=str(q.get("id") or ""),
                type=str(q.get("type") or "mcq"),
                stem=str(q.get("stem") or ""),
                choices=[str(c) for c in (q.get("choices") or [])],
            )
        )
    return out


def _progress_out(raw: dict | None) -> LessonProgressOut:
    data = raw or {}
    completed_at = data.get("completed_at")
    if isinstance(completed_at, datetime):
        completed_at = completed_at
    return LessonProgressOut(
        status=str(data.get("status") or "not_started"),
        score_percent=data.get("score_percent"),
        completed_at=completed_at,
        attempt_count=int(data.get("attempt_count") or 0),
    )


def _lesson_goal_out(body: dict, goal_id: str | None) -> LessonGoalOut:
    gid = goal_id or "general_english"
    try:
        label = profile_for_goal(LearningGoal(gid)).label
    except ValueError:
        label = gid.replace("_", " ").title()
    return LessonGoalOut(id=gid, label=label)


def _narrative_out(narrative) -> LessonNarrativeOut:
    return LessonNarrativeOut(
        reason_selected=narrative.reason_selected,
        why_this_lesson=narrative.why_this_lesson,
        student_focus=list(narrative.student_focus),
        expected_improvement=list(narrative.expected_improvement),
        challenge_reason=narrative.challenge_reason,
        reward=narrative.reward,
        next_after_this=narrative.next_after_this,
        coach_summary=narrative.coach_summary,
    )


def _after_lesson_out(narrative) -> AfterLessonOut:
    return AfterLessonOut(
        headline=narrative.headline,
        summary=narrative.summary,
        improved=list(narrative.improved),
        needs_practice=list(narrative.needs_practice),
        next_lesson_teaser=narrative.next_lesson_teaser,
        coach_summary=narrative.coach_summary,
    )


async def build_lesson_experience_bundle(
    db: AsyncSession,
    *,
    item: LanguageContentItem,
    student_id: int,
    language_id: int,
    progress_out: dict | None = None,
    reservation: LanguageListeningReservation | None = None,
    post_lesson: PostLessonFacts | None = None,
    official_cefr: str | None = None,
    target_cefr: str | None = None,
    readiness_band: str | None = None,
    estimated_lessons_remaining: int | None = None,
    can_start_promotion_test: bool = False,
    readiness_score: float | None = None,
) -> LessonExperienceBundleOut:
    """Assemble canonical lesson bundle — lesson scope only."""
    body = lesson_body_for_student(item)
    audio_url, audio_available = await resolve_listening_audio(db, item)
    official = official_cefr or await _official_listening_cefr(
        db, student_id=student_id, language_id=language_id
    )
    target = target_cefr or await _target_listening_cefr(
        db, student_id=student_id, language_id=language_id
    )
    lesson_level = item.level.value if item.level else "A1"
    goal_id = _resolve_lesson_goal_id(body)

    signals = extract_signals(body, cefr_level=lesson_level)
    lesson_facts = assemble_lesson_facts(
        body,
        lesson_id=item.id,
        lesson_title=item.title,
        lesson_level=lesson_level,
        official_level=official,
        journey_target_level=target,
    )
    explain_facts = build_explainability_facts(
        signals,
        official_level=official,
        journey_target_level=target,
        lesson_level=lesson_level,
    )
    progression = assemble_progression_facts(
        official_level=official,
        journey_target_level=target,
        readiness_band=readiness_band,
        estimated_lessons_remaining=estimated_lessons_remaining,
        can_start_promotion_test=can_start_promotion_test,
        readiness_score=readiness_score,
    )
    narrative = build_lesson_narrative(lesson_facts, explain_facts, progression=progression)

    progress = _progress_out(progress_out)
    lifecycle = _map_lifecycle(
        reservation=reservation,
        progress_status=progress.status,
        has_after_lesson=post_lesson is not None,
    )

    after = None
    if post_lesson is not None:
        after_narr = build_after_lesson_narrative(
            lesson_facts, explain_facts, post_lesson, progression=progression
        )
        after = _after_lesson_out(after_narr)
        lifecycle = _map_lifecycle(
            reservation=reservation,
            progress_status=progress.status,
            has_after_lesson=True,
        )

    pinned_until = None
    if reservation is not None:
        pinned_until = "completed"

    return LessonExperienceBundleOut(
        lesson_id=item.id,
        lifecycle_state=lifecycle,  # type: ignore[arg-type]
        official_level=str(official or lesson_level).upper(),
        lesson_level=lesson_level,
        level_note=narrative.level_note,
        lesson_title=item.title,
        lesson_type=_lesson_type_from_body(body),
        situation=narrative.situation_label,
        lesson_goal=_lesson_goal_out(body, goal_id),
        narrative=_narrative_out(narrative),
        playback=LessonPlaybackOut(
            instructions=body.get("instructions"),
            questions=_questions_out(body),
            audio_url=audio_url,
            audio_available=audio_available,
            progress=progress,
        ),
        after_lesson=after,
        meta=LessonExperienceMetaOut(
            builder_version=BUILDER_VERSION,
            facts_schema_version=FACTS_SCHEMA_VERSION,
            reservation_id=str(reservation.id) if reservation else None,
            pinned_until=pinned_until,
            activity_session_id=body.get("activity_session_id"),
            grammar_id=body.get("grammar_id"),
            grammar_title=body.get("grammar_title"),
        ),
    )


async def build_lesson_experience_legacy_payload(
    db: AsyncSession,
    *,
    item: LanguageContentItem,
    student_id: int,
    language_id: int,
    progress_out: dict | None = None,
    reservation: LanguageListeningReservation | None = None,
) -> dict:
    """Backward-compatible ListeningLessonOut-shaped dict from canonical builder."""
    bundle = await build_lesson_experience_bundle(
        db,
        item=item,
        student_id=student_id,
        language_id=language_id,
        progress_out=progress_out,
        reservation=reservation,
    )
    return bundle_to_legacy_payload(bundle)
