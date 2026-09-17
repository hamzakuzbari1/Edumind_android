"""Submit reading/listening lessons — single progress path."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageContentProgressStatus, LanguageSkill
from app.models.language.path import LanguagePathItem
from app.models.language.progress import LanguageListeningProgress, LanguageReadingProgress
from app.services.language_adaptive_service import record_lesson_result
from app.services.language_analytics_service import refresh_language_analytics
from app.services.language_curriculum_service import credit_skill_objectives
from app.services.language_xp_service import award_language_xp
from app.services.language_content_service import (
    get_answer_key,
    get_listening_lesson,
    get_reading_lesson,
    pass_threshold_for_item,
)
from app.services.language_engagement_service import record_activity, upsert_vocabulary_from_lesson
from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
from app.services.language_grammar_skill_context import complete_current_skill_activity_async
from app.services.language_learner_events import record_lesson_questions
from app.services.language_placement_scoring_service import normalize_choice_answer, score_mcq

logger = logging.getLogger(__name__)


def _reading_question_results(body: dict | None, answers: dict[str, dict]) -> list[dict]:
    """Per-question results for the reading report: correctness + explanation + supporting quote."""
    out: list[dict] = []
    for q in (body or {}).get("questions") or []:
        qid = q.get("id")
        resp = answers.get(qid) or answers.get(str(qid)) or {}
        ci = q.get("correct_index")
        out.append({
            "id": qid,
            "type": q.get("type") or "detail",
            "stem": q.get("stem") or "",
            "selected_index": normalize_choice_answer(resp),
            "correct_index": ci,
            "is_correct": score_mcq(resp, {"correct_index": ci}) > 0,
            "explanation": q.get("explanation") or "",
            "evidence_quote": q.get("evidence_quote") or "",
        })
    return out
from app.services.language_subscription_service import get_default_language


def _score_answers(body: dict | None, answers: dict[str, dict]) -> tuple[float, int, int]:
    keys = get_answer_key(body)
    total = len(keys)
    if total == 0:
        return 0.0, 0, 0
    earned = 0.0
    for qid, correct_idx in keys.items():
        resp = answers.get(qid) or answers.get(str(qid)) or {}
        earned += score_mcq(resp, {"correct_index": correct_idx}, max_points=1)
    score_percent = round(100.0 * earned / total, 1)
    return score_percent, int(earned), total


async def _sync_path_item(db: AsyncSession, *, student_id: int, content_item_id: int) -> None:
    from app.models.language.path import LanguageLearningPath

    result = await db.execute(
        select(LanguagePathItem)
        .join(LanguageLearningPath, LanguageLearningPath.id == LanguagePathItem.path_id)
        .where(
            LanguageLearningPath.student_id == student_id,
            LanguagePathItem.content_item_id == content_item_id,
        )
    )
    for item in result.scalars().all():
        item.status = LanguageContentProgressStatus.completed


async def _upsert_progress(
    db: AsyncSession,
    *,
    student_id: int,
    item: LanguageContentItem,
    skill: LanguageSkill,
    score_percent: float,
    passed: bool,
):
    if skill == LanguageSkill.reading:
        result = await db.execute(
            select(LanguageReadingProgress).where(
                LanguageReadingProgress.student_id == student_id,
                LanguageReadingProgress.content_item_id == item.id,
            )
        )
        progress = result.scalar_one_or_none()
        if not progress:
            progress = LanguageReadingProgress(student_id=student_id, content_item_id=item.id)
            db.add(progress)
    else:
        result = await db.execute(
            select(LanguageListeningProgress).where(
                LanguageListeningProgress.student_id == student_id,
                LanguageListeningProgress.content_item_id == item.id,
            )
        )
        progress = result.scalar_one_or_none()
        if not progress:
            progress = LanguageListeningProgress(student_id=student_id, content_item_id=item.id)
            db.add(progress)

    progress.attempt_count = int(progress.attempt_count or 0) + 1
    progress.score_percent = score_percent
    progress.status = (
        LanguageContentProgressStatus.completed
        if passed
        else LanguageContentProgressStatus.in_progress
    )
    if passed and not progress.completed_at:
        progress.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return progress


def _reading_wpm(body: dict | None, duration_seconds: int | None) -> int | None:
    """Words-per-minute over the passage, when a sensible reading time was reported."""
    if not duration_seconds or duration_seconds <= 0:
        return None
    passage = ((body or {}).get("passage") or "").strip()
    words = len(passage.split())
    if words < 5:
        return None
    wpm = round(words / (duration_seconds / 60.0))
    # Guard against absurd values (instant submit / left the tab open for hours).
    return wpm if 20 <= wpm <= 1500 else None


async def submit_reading(
    db: AsyncSession,
    *,
    student_id: int,
    content_id: int,
    answers: dict[str, dict],
    duration_seconds: int | None = None,
) -> dict:
    item, _existing = await get_reading_lesson(db, student_id=student_id, content_id=content_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    score_percent, correct, total = _score_answers(item.body_json, answers)
    wpm = _reading_wpm(item.body_json, duration_seconds)
    threshold = pass_threshold_for_item(item)
    passed = score_percent >= threshold
    progress = await _upsert_progress(
        db, student_id=student_id, item=item, skill=LanguageSkill.reading, score_percent=score_percent, passed=passed
    )
    language = await get_default_language(db)
    if passed:
        await _sync_path_item(db, student_id=student_id, content_item_id=item.id)
        vocab = (item.body_json or {}).get("vocabulary") or []
        await upsert_vocabulary_from_lesson(db, student_id=student_id, language_id=language.id, lemmas=vocab)
        await award_language_xp(db, student_id=student_id, language_id=language.id, activity="lesson", key=f"lesson:{item.id}")
    event = "reading_lesson_completed" if passed else "reading_lesson_submitted"
    await record_activity(
        db,
        student_id=student_id,
        language_id=language.id,
        event_type=event,
        skill=LanguageSkill.reading,
        payload_json={
            "content_item_id": item.id,
            "title": item.title,
            "score_percent": score_percent,
            "passed": passed,
            "wpm": wpm,
        },
    )
    await refresh_language_analytics(db, student_id=student_id, language_id=language.id)
    # Adaptive reading: nudge the reading level by this result so the next passage adapts.
    from app.models.language.analytics import LanguageAnalytics
    from app.services.language_reading_service import nudge_reading_level

    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language.id})
    if analytics is not None:
        new_level = nudge_reading_level(analytics.reading_level, score_percent)
        if new_level != analytics.reading_level:
            analytics.reading_level = new_level
    await record_lesson_result(
        db, student_id=student_id, language_id=language.id, skill=LanguageSkill.reading, score_percent=score_percent
    )
    await credit_skill_objectives(
        db, student_id=student_id, language_id=language.id, skill=LanguageSkill.reading,
        score_percent=score_percent, passed=passed,
    )
    question_results = _reading_question_results(item.body_json, answers)
    await record_lesson_questions(
        db, student_id=student_id, language_id=language.id, skill=LanguageSkill.reading,
        level=item.level, question_results=question_results, source="reading",
    )
    if passed:
        try:
            await complete_current_skill_activity_async(
                db,
                student_id=student_id,
                language_id=language.id,
                skill=GrammarEvidenceSourceSkill.reading,
                score=score_percent,
                activity_id=f"reading:{item.id}:{progress.attempt_count}",
                activity_type="reading",
                lesson_id=str(item.id),
                context=f"reading:{item.id}",
                observation_id=f"ev_reading_{item.id}_{progress.attempt_count}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("grammar reading evidence completion failed: %s", exc)
    return {
        "content_item_id": item.id,
        "score_percent": score_percent,
        "passed": passed,
        "status": progress.status.value,
        "attempt_count": progress.attempt_count,
        "completed_at": progress.completed_at,
        "correct_count": correct,
        "total_questions": total,
        "question_results": question_results,
        "reading_wpm": wpm,
    }


async def submit_listening(
    db: AsyncSession,
    *,
    student_id: int,
    content_id: int,
    answers: dict[str, dict],
) -> dict:
    item, _existing, _url, _avail = await get_listening_lesson(db, student_id=student_id, content_id=content_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    score_percent, correct, total = _score_answers(item.body_json, answers)
    threshold = pass_threshold_for_item(item)
    passed = score_percent >= threshold
    progress = await _upsert_progress(
        db, student_id=student_id, item=item, skill=LanguageSkill.listening, score_percent=score_percent, passed=passed
    )
    language = await get_default_language(db)
    if passed:
        await _sync_path_item(db, student_id=student_id, content_item_id=item.id)
        vocab = (item.body_json or {}).get("vocabulary") or []
        await upsert_vocabulary_from_lesson(db, student_id=student_id, language_id=language.id, lemmas=vocab)
        await award_language_xp(db, student_id=student_id, language_id=language.id, activity="lesson", key=f"lesson:{item.id}")
    event = "listening_lesson_completed" if passed else "listening_lesson_submitted"
    await record_activity(
        db,
        student_id=student_id,
        language_id=language.id,
        event_type=event,
        skill=LanguageSkill.listening,
        payload_json={
            "content_item_id": item.id,
            "title": item.title,
            "score_percent": score_percent,
            "passed": passed,
        },
    )
    await refresh_language_analytics(db, student_id=student_id, language_id=language.id)
    await record_lesson_result(
        db, student_id=student_id, language_id=language.id, skill=LanguageSkill.listening, score_percent=score_percent
    )
    await credit_skill_objectives(
        db, student_id=student_id, language_id=language.id, skill=LanguageSkill.listening,
        score_percent=score_percent, passed=passed,
    )
    question_results = _reading_question_results(item.body_json, answers)
    await record_lesson_questions(
        db, student_id=student_id, language_id=language.id, skill=LanguageSkill.listening,
        level=item.level, question_results=question_results, source="listening",
    )
    if passed:
        try:
            await complete_current_skill_activity_async(
                db,
                student_id=student_id,
                language_id=language.id,
                skill=GrammarEvidenceSourceSkill.listening,
                score=score_percent,
                activity_id=f"listening:{item.id}:{progress.attempt_count}",
                activity_type="listening",
                lesson_id=str(item.id),
                context=f"listening:{item.id}",
                observation_id=f"ev_listening_{item.id}_{progress.attempt_count}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("grammar listening evidence completion failed: %s", exc)
    # Adaptive: nudge the listening level so future lessons track performance (generic CEFR nudge).
    from app.models.language.analytics import LanguageAnalytics
    from app.services.language_reading_service import nudge_reading_level

    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language.id})
    if analytics is not None:
        new_level = nudge_reading_level(analytics.listening_level, score_percent)
        if new_level != analytics.listening_level:
            analytics.listening_level = new_level
    return {
        "content_item_id": item.id,
        "score_percent": score_percent,
        "passed": passed,
        "status": progress.status.value,
        "attempt_count": progress.attempt_count,
        "completed_at": progress.completed_at,
        "correct_count": correct,
        "total_questions": total,
        "question_results": question_results,
        # Revealed only after submitting, so the listening test itself stays audio-only.
        "transcript": (item.body_json or {}).get("audio_transcript") or "",
    }
