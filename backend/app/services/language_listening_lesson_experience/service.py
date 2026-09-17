"""Orchestration helpers for Lesson Experience Builder (Phase 2.3)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.content import LanguageContentItem
from app.models.language.reservation import LanguageListeningReservation
from app.schemas.language_listening_bundles import (
    LessonExperienceBundleOut,
    ListeningLessonSubmitBundleOut,
)
from app.services.language_learning_facts.types import PostLessonFacts
from app.services.language_listening_lesson_experience.builder import (
    build_lesson_experience_bundle,
    build_lesson_experience_legacy_payload,
)
from app.services.language_listening_lesson_experience.legacy_adapter import bundle_to_legacy_payload
from app.services.language_listening_reservation.storage import load_reservation_by_content
from app.services.language_listening_service import _official_listening_cefr, _target_listening_cefr
from app.services.language_promotion_readiness import evaluate_listening_promotion_readiness
from app.services.language_promotion_readiness.types import ReadinessStatus
from app.services.language_promotion_test import check_promotion_test_eligibility


async def _load_reservation(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    content_item_id: int,
) -> LanguageListeningReservation | None:
    return await load_reservation_by_content(
        db,
        student_id=student_id,
        language_id=language_id,
        content_item_id=content_item_id,
    )


async def _progression_context(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
) -> dict:
    official = official_cefr or await _official_listening_cefr(
        db, student_id=student_id, language_id=language_id
    )
    target = await _target_listening_cefr(db, student_id=student_id, language_id=language_id)
    readiness = await evaluate_listening_promotion_readiness(
        db, student_id=student_id, language_id=language_id, official_cefr=official
    )
    eligibility = await check_promotion_test_eligibility(
        db, student_id=student_id, language_id=language_id
    )
    can_start = bool(
        eligibility.eligible and readiness.status == ReadinessStatus.PROMOTION_AVAILABLE
    )
    return {
        "official_cefr": official,
        "target_cefr": target,
        "readiness_band": readiness.status.value if readiness.status else "NOT_READY",
        "estimated_lessons_remaining": readiness.estimated_remaining,
        "can_start_promotion_test": can_start,
        "readiness_score": float(readiness.readiness_score) if readiness.readiness_score is not None else None,
    }


async def build_student_lesson_bundle(
    db: AsyncSession,
    *,
    item: LanguageContentItem,
    student_id: int,
    language_id: int,
    progress_out: dict | None = None,
    post_lesson: PostLessonFacts | None = None,
) -> LessonExperienceBundleOut:
    reservation = await _load_reservation(
        db,
        student_id=student_id,
        language_id=language_id,
        content_item_id=item.id,
    )
    ctx = await _progression_context(db, student_id=student_id, language_id=language_id)
    return await build_lesson_experience_bundle(
        db,
        item=item,
        student_id=student_id,
        language_id=language_id,
        progress_out=progress_out,
        reservation=reservation,
        post_lesson=post_lesson,
        official_cefr=ctx["official_cefr"],
        target_cefr=ctx["target_cefr"],
        readiness_band=ctx["readiness_band"],
        estimated_lessons_remaining=ctx["estimated_lessons_remaining"],
        can_start_promotion_test=ctx["can_start_promotion_test"],
        readiness_score=ctx["readiness_score"],
    )


async def build_student_lesson_legacy(
    db: AsyncSession,
    *,
    item: LanguageContentItem,
    student_id: int,
    language_id: int,
    progress_out: dict | None = None,
) -> dict:
    bundle = await build_student_lesson_bundle(
        db,
        item=item,
        student_id=student_id,
        language_id=language_id,
        progress_out=progress_out,
    )
    return bundle_to_legacy_payload(bundle)


async def build_submit_bundle(
    db: AsyncSession,
    *,
    item: LanguageContentItem,
    student_id: int,
    language_id: int,
    progress_out: dict,
    submit_result: dict,
) -> ListeningLessonSubmitBundleOut:
    post = PostLessonFacts(
        score_percent=float(submit_result.get("score_percent") or 0),
        passed=bool(submit_result.get("passed")),
        correct_count=int(submit_result.get("correct_count") or 0),
        total_questions=int(submit_result.get("total_questions") or 0),
    )
    bundle = await build_student_lesson_bundle(
        db,
        item=item,
        student_id=student_id,
        language_id=language_id,
        progress_out=progress_out,
        post_lesson=post,
    )
    return ListeningLessonSubmitBundleOut(
        bundle=bundle,
        passed=bool(submit_result.get("passed")),
        score_percent=float(submit_result.get("score_percent") or 0),
        correct_count=int(submit_result.get("correct_count") or 0),
        total_questions=int(submit_result.get("total_questions") or 0),
        question_results=list(submit_result.get("question_results") or []),
    )
