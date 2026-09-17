"""Listening Promotion Test Engine (Phase 5.4).

Official CEFR -> Promotion Readiness -> Eligibility -> Session -> Result -> Official Promotion.

POLICY: Never mutates official_listening_cefr — grading and history only.
Official Promotion is the sole runtime writer of official_listening_cefr.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.enums import LanguageLevel
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR
from app.services.language_listening_progression.locking import lock_listening_progression_row
from app.services.language_progression_service import ensure_progression_row, get_official_cefr, progression_enabled
from app.services.language_promotion_readiness import ReadinessStatus, evaluate_listening_promotion_readiness
from app.services.language_promotion_test.builder import build_promotion_test_session
from app.services.language_promotion_test.config import DEFAULT_PROMOTION_TEST_CONFIG, PromotionTestConfig
from app.services.language_promotion_test.scoring import grade_promotion_test_session
from app.services.language_promotion_test.session import get_session, pop_session, register_session
from app.services.language_promotion_test.session_storage import attempt_exists_for_session
from app.services.language_promotion_test.storage import _tests_bucket, save_promotion_test_attempt
from app.services.language_promotion_test.telemetry import build_promotion_test_result
from app.services.language_promotion_test.types import PromotionTestEligibility, PromotionTestResult, PromotionTestSession


def _next_cefr(level: str) -> str:
    try:
        current = LanguageLevel(level.upper())
    except ValueError:
        return level.upper()
    nxt = CEFR_RANK.get(current, 1) + 1
    if nxt in RANK_CEFR:
        return RANK_CEFR[nxt].value
    return current.value


async def check_promotion_test_eligibility(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
) -> PromotionTestEligibility:
    readiness = await evaluate_listening_promotion_readiness(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=official_cefr,
    )
    level = readiness.official_cefr
    target = _next_cefr(level)
    if readiness.status != ReadinessStatus.PROMOTION_AVAILABLE:
        return PromotionTestEligibility(
            eligible=False,
            reason=(
                f"Promotion test requires PROMOTION_AVAILABLE readiness "
                f"(current: {readiness.status.value}, score: {readiness.readiness_score})."
            ),
            official_cefr=level,
            target_cefr=target,
            readiness_score=readiness.readiness_score,
            readiness_status=readiness.status.value,
        )
    return PromotionTestEligibility(
        eligible=True,
        reason="Promotion readiness is PROMOTION_AVAILABLE — test may begin.",
        official_cefr=level,
        target_cefr=target,
        readiness_score=readiness.readiness_score,
        readiness_status=readiness.status.value,
    )


async def create_listening_promotion_test_session(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    official_cefr: str | None = None,
    config: PromotionTestConfig = DEFAULT_PROMOTION_TEST_CONFIG,
) -> PromotionTestSession | PromotionTestEligibility:
    eligibility = await check_promotion_test_eligibility(
        db,
        student_id=student_id,
        language_id=language_id,
        official_cefr=official_cefr,
    )
    if not eligibility.eligible:
        return eligibility

    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        return PromotionTestEligibility(
            eligible=False,
            reason=(
                "Listening progression is not available. "
                "Enable LANG_PROGRESSION_ENABLED and complete language onboarding."
                if not progression_enabled()
                else "Listening progression could not be initialized (missing analytics)."
            ),
            official_cefr=eligibility.official_cefr,
            target_cefr=eligibility.target_cefr,
            readiness_score=eligibility.readiness_score,
            readiness_status=eligibility.readiness_status,
        )

    row = await lock_listening_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        return PromotionTestEligibility(
            eligible=False,
            reason="Listening progression row could not be locked.",
            official_cefr=eligibility.official_cefr,
            target_cefr=eligibility.target_cefr,
            readiness_score=eligibility.readiness_score,
            readiness_status=eligibility.readiness_status,
        )

    state = _tests_bucket(dict(row.promotion_readiness_json or {}))
    attempts = state.get("attempts") or []
    used_lesson_ids = set(state.get("used_lesson_ids") or [])
    used_sequences = {tuple(seq) for seq in (state.get("used_sequences") or []) if isinstance(seq, list)}

    session = build_promotion_test_session(
        student_id=student_id,
        language_id=language_id,
        official_cefr=eligibility.official_cefr,
        target_cefr=eligibility.target_cefr,
        attempt_number=len(attempts) + 1,
        used_lesson_ids=used_lesson_ids,
        used_sequences=used_sequences,
        config=config,
    )
    return await register_session(db, session, locked_row=row)


async def submit_listening_promotion_test(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    session_id: str,
    answers: dict[str, int],
) -> PromotionTestResult | None:
    """Grade a promotion test session and persist history — never promotes Official CEFR."""
    row = await lock_listening_progression_row(
        db, student_id=student_id, language_id=language_id
    )
    if row is None:
        return None

    bucket = _tests_bucket(dict(row.promotion_readiness_json or {}))
    if attempt_exists_for_session(bucket, session_id):
        return None

    session = await get_session(
        db,
        session_id,
        student_id=student_id,
        language_id=language_id,
    )
    if session is None:
        return None
    if session.student_id != student_id or session.language_id != language_id:
        return None

    breakdown, correct_count = grade_promotion_test_session(session, answers)
    result = build_promotion_test_result(
        session=session,
        breakdown=breakdown,
        correct_count=correct_count,
    )
    await save_promotion_test_attempt(
        db,
        student_id=student_id,
        language_id=language_id,
        session=session,
        result=result,
        row=row,
    )
    await pop_session(
        db,
        session_id,
        student_id=student_id,
        language_id=language_id,
        locked_row=row,
    )
    return result
