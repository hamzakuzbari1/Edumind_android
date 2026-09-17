"""Build language access payload and FastAPI subscription guards."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_student_actor
from app.db.session import get_db
from app.models.language.analytics import LanguageAnalytics
from app.models.language.profile import LanguageStudentProfile
from app.models.user import User
from app.models.language.exam import LanguageExamSession
from app.schemas.language import (
    LanguageAccessOut,
    LanguageProductOut,
    LanguageSkillLevelsOut,
    PlacementCorrectionOut,
    PlacementRecommendationOut,
)
from app.services.language_level_utils import SKILL_LABELS_AR, primary_focus_and_strength
from app.services.language_subscription_access_service import (
    is_language_subscription_active,
    language_subscription_status,
)
from app.services.language_subscription_service import (
    get_default_language,
    get_default_product,
    get_student_subscription,
)


async def _latest_placement_recommendation(
    db: AsyncSession, *, student_id: int, language_id: int
) -> PlacementRecommendationOut | None:
    """Pull the most recent completed exam's actionable guidance to steer the learner's first steps."""
    row = (
        await db.execute(
            select(LanguageExamSession)
            .where(
                LanguageExamSession.student_id == student_id,
                LanguageExamSession.language_id == language_id,
                LanguageExamSession.status == "completed",
            )
            .order_by(LanguageExamSession.completed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    report = (row.assessment_report if row else None) or {}
    if not report:
        return None
    corrections = [
        PlacementCorrectionOut(
            original=str(e.get("original_text", "")),
            corrected=str(e.get("corrected_text", "")),
            rule=str(e.get("rule_explanation", "")),
        )
        for e in (report.get("detected_errors") or [])[:3]
    ]
    return PlacementRecommendationOut(
        topic=str(report.get("recommended_starting_lesson_topic", "")),
        weakest_skill=str(report.get("weakest_skill", "")),
        summary=str(report.get("summary", "")),
        corrections=corrections,
    )


async def build_language_access(db: AsyncSession, student_id: int) -> LanguageAccessOut:
    product = await get_default_product(db)
    language = await get_default_language(db)
    sub = await get_student_subscription(db, student_id, product.id)

    status_val = language_subscription_status(sub)
    subscribed = sub is not None and is_language_subscription_active(sub)

    profile_result = await db.execute(
        select(LanguageStudentProfile).where(
            LanguageStudentProfile.student_id == student_id,
            LanguageStudentProfile.language_id == language.id,
        )
    )
    profile = profile_result.scalar_one_or_none()

    placement_completed = bool(profile and profile.placement_completed_at)
    onboarding_step = profile.onboarding_step.value if profile else None
    next_allowed_retake_date = profile.next_allowed_retake_date if profile else None

    levels = LanguageSkillLevelsOut()
    analytics_result = await db.execute(
        select(LanguageAnalytics).where(
            LanguageAnalytics.student_id == student_id,
            LanguageAnalytics.language_id == language.id,
        )
    )
    analytics = analytics_result.scalar_one_or_none()
    if analytics:
        levels.reading = analytics.reading_level.value if analytics.reading_level else None
        levels.listening = analytics.listening_level.value if analytics.listening_level else None
        levels.writing = analytics.writing_level.value if analytics.writing_level else None
        levels.speaking = analytics.speaking_level.value if analytics.speaking_level else None
        focus, strength = primary_focus_and_strength(
            {
                "reading": levels.reading,
                "listening": levels.listening,
                "writing": levels.writing,
                "speaking": levels.speaking,
            }
        )
        levels.primary_focus_skill = focus
        levels.strength_skill = strength
        if focus:
            levels.primary_focus_label_ar = SKILL_LABELS_AR.get(focus, focus)
        if strength:
            levels.strength_label_ar = SKILL_LABELS_AR.get(strength, strength)

    redirect = None
    placement_recommendation = None
    if not subscribed:
        redirect = "/student/languages/subscribe"
    elif not placement_completed:
        # The interactive AI exam is now the entry assessment (replaces the old placement wizard).
        redirect = "/student/languages/exam"
    else:
        placement_recommendation = await _latest_placement_recommendation(
            db, student_id=student_id, language_id=language.id
        )

    return LanguageAccessOut(
        subscribed=subscribed,
        status=status_val,
        expires_at=sub.expires_at if sub else None,
        activated_at=sub.activated_at if sub else None,
        placement_completed=placement_completed,
        next_allowed_retake_date=next_allowed_retake_date,
        onboarding_step=onboarding_step,
        product=LanguageProductOut(
            id=product.id,
            slug=product.slug,
            name_ar=product.name_ar,
            description_ar=product.description_ar,
            price=product.price,
            currency=product.currency,
            term_days=product.term_days,
        ),
        levels=levels,
        target_level=profile.target_level.value if profile and profile.target_level else None,
        target_date=profile.target_date if profile else None,
        target_progress_percent=profile.target_progress_percent if profile else None,
        estimated_time_to_next_level=(
            profile.estimated_time_to_next_level
            if profile and profile.estimated_time_to_next_level
            else (analytics.estimated_time_to_next_level if analytics else None)
        ),
        certificate_level=profile.certificate_level.value if profile and profile.certificate_level else None,
        certificate_awarded_at=profile.certificate_awarded_at if profile else None,
        placement_recommendation=placement_recommendation,
        redirect=redirect,
    )


def require_active_language_subscription():
    async def checker(
        student: User = Depends(require_student_actor()),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        access = await build_language_access(db, student.id)
        if not access.subscribed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "language_subscription_required",
                    "message": "Your language learning subscription is inactive",
                    "status": access.status,
                    "redirect": "/student/languages/subscribe",
                },
            )
        return student

    return checker


def require_language_learning_ready():
    """Active subscription and completed placement — required for lessons and progress."""

    async def checker(
        student: User = Depends(require_student_actor()),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        access = await build_language_access(db, student.id)
        if not access.subscribed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "language_subscription_required",
                    "message": "Your language learning subscription is inactive",
                    "status": access.status,
                    "redirect": "/student/languages/subscribe",
                },
            )
        if not access.placement_completed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "language_placement_required",
                    "message": "Take the AI level exam first",
                    "redirect": "/student/languages/exam",
                },
            )
        return student

    return checker
