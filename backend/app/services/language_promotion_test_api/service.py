"""API orchestration for the Listening Promotion Test — reuses Phase 5.4 engine only."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.language_promotion_test import (
    PromotionTestActiveSessionOut,
    PromotionTestAssessmentOut,
    PromotionTestAttemptSummaryOut,
    PromotionTestEligibilityOut,
    PromotionTestLatestResultOut,
    PromotionTestReadinessOut,
    PromotionTestStabilityOut,
    PromotionTestStartOut,
    PromotionTestStatusOut,
    PromotionTestSubmitOut,
    PromotionTestScoreBreakdownOut,
)
from app.services.language_promotion_readiness import evaluate_listening_promotion_readiness
from app.services.language_promotion_stability import evaluate_listening_promotion_stability
from app.services.language_promotion_test import (
    check_promotion_test_eligibility,
    create_listening_promotion_test_session,
    submit_listening_promotion_test,
)
from app.services.language_promotion_test.session import find_active_session, get_session
from app.services.language_promotion_test.session_storage import inspect_promotion_test_session
from app.services.language_promotion_test.storage import load_promotion_test_state
from app.services.language_promotion_test.types import PromotionTestEligibility, PromotionTestSession
from app.services.language_progression_service import PROGRESSION_UNAVAILABLE_REASON, ensure_progression_row


class PromotionTestApiError(Exception):
    """Maps API-layer failures to HTTP status codes without modifying the engine."""

    def __init__(self, status_code: int, detail: dict | str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


def _utc_from_epoch(value: float) -> datetime:
    return datetime.fromtimestamp(value, tz=timezone.utc)


def _attempt_for_session(state: dict, session_id: str) -> dict | None:
    for attempt in reversed(state.get("attempts") or []):
        if isinstance(attempt, dict) and str(attempt.get("session_id")) == session_id:
            return attempt
    return None


def _eligibility_out(eligibility: PromotionTestEligibility) -> PromotionTestEligibilityOut:
    return PromotionTestEligibilityOut(
        eligible=eligibility.eligible,
        reason=eligibility.reason,
        official_cefr=eligibility.official_cefr,
        target_cefr=eligibility.target_cefr,
        readiness_score=eligibility.readiness_score,
        readiness_status=eligibility.readiness_status,
    )


def _session_start_out(session: PromotionTestSession) -> PromotionTestStartOut:
    return PromotionTestStartOut(
        session_id=session.session_id,
        official_cefr=session.official_cefr,
        target_cefr=session.target_cefr,
        attempt_number=session.attempt_number,
        expires_at=_utc_from_epoch(session.expires_at),
        assessments=[
            PromotionTestAssessmentOut(**assessment.to_public_dict())  # type: ignore[arg-type]
            for assessment in session.assessments
        ],
    )


def _active_session_out(session: PromotionTestSession) -> PromotionTestActiveSessionOut:
    return PromotionTestActiveSessionOut(
        session_id=session.session_id,
        official_cefr=session.official_cefr,
        target_cefr=session.target_cefr,
        attempt_number=session.attempt_number,
        assessment_count=len(session.assessments),
        expires_at=_utc_from_epoch(session.expires_at),
    )


def _result_to_submit_out(result) -> PromotionTestSubmitOut:
    breakdown = result.score_breakdown
    telemetry = result.telemetry
    return PromotionTestSubmitOut(
        session_id=result.session_id,
        overall_score=result.overall_score,
        result=result.result.value,
        objective_scores=dict(result.objective_scores),
        strengths=list(result.strengths),
        weaknesses=list(result.weaknesses),
        recommendation=result.recommendation,
        score_breakdown=PromotionTestScoreBreakdownOut(
            overall_score=breakdown.overall_score,
            objective_scores=dict(breakdown.objective_scores),
            evidence_score=breakdown.evidence_score,
            consistency_score=breakdown.consistency_score,
            coverage_score=breakdown.coverage_score,
            exam_confidence=breakdown.exam_confidence,
        ),
        attempt_number=telemetry.attempt_number,
        official_cefr=telemetry.official_cefr,
        target_cefr=telemetry.target_cefr,
        assessments_correct=telemetry.assessments_correct,
        assessments_total=telemetry.assessments_total,
    )


async def get_listening_promotion_test_status(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> PromotionTestStatusOut:
    eligibility = await check_promotion_test_eligibility(
        db, student_id=student_id, language_id=language_id
    )
    readiness = await evaluate_listening_promotion_readiness(
        db, student_id=student_id, language_id=language_id
    )
    stability = await evaluate_listening_promotion_stability(
        db, student_id=student_id, language_id=language_id
    )
    state = await load_promotion_test_state(db, student_id=student_id, language_id=language_id)
    attempts = state.get("attempts") or []
    last_attempt_raw = attempts[-1] if attempts else None
    active = await find_active_session(db, student_id=student_id, language_id=language_id)

    last_attempt = None
    latest_result = None
    if isinstance(last_attempt_raw, dict):
        last_attempt = PromotionTestAttemptSummaryOut(
            session_id=str(last_attempt_raw.get("session_id", "")),
            attempt_number=int(last_attempt_raw.get("attempt_number", 0)),
            official_cefr=str(last_attempt_raw.get("official_cefr", "")),
            target_cefr=str(last_attempt_raw.get("target_cefr", "")),
            overall_score=float(last_attempt_raw.get("overall_score", 0.0)),
            result=str(last_attempt_raw.get("result", "")),
        )
        latest_result = PromotionTestLatestResultOut(
            session_id=last_attempt.session_id,
            overall_score=last_attempt.overall_score,
            result=last_attempt.result,
            recommendation=str(last_attempt_raw.get("recommendation", "")),
            objective_scores={
                str(k): float(v)
                for k, v in (last_attempt_raw.get("objective_scores") or {}).items()
            },
        )

    return PromotionTestStatusOut(
        eligibility=_eligibility_out(eligibility),
        readiness=PromotionTestReadinessOut(
            official_cefr=readiness.official_cefr,
            readiness_score=readiness.readiness_score,
            status=readiness.status.value,
            estimated_remaining=readiness.estimated_remaining,
            primary_blockers=list(readiness.primary_blockers),
        ),
        stability=PromotionTestStabilityOut(
            promotion_confidence=stability.promotion_confidence,
            readiness_stability=stability.readiness_stability,
            prediction=stability.prediction.value,
        ),
        active_session=_active_session_out(active) if active else None,
        last_attempt=last_attempt,
        latest_result=latest_result,
    )


async def start_listening_promotion_test(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> PromotionTestStartOut:
    if await ensure_progression_row(db, student_id=student_id, language_id=language_id) is None:
        raise PromotionTestApiError(
            503,
            {
                "eligible": False,
                "reason": PROGRESSION_UNAVAILABLE_REASON,
                "progression_available": False,
            },
        )

    created = await create_listening_promotion_test_session(
        db, student_id=student_id, language_id=language_id
    )
    if isinstance(created, PromotionTestEligibility):
        raise PromotionTestApiError(
            403,
            {
                "eligible": False,
                "reason": created.reason,
                "official_cefr": created.official_cefr,
                "target_cefr": created.target_cefr,
                "readiness_score": created.readiness_score,
                "readiness_status": created.readiness_status,
            },
        )
    return _session_start_out(created)


async def submit_listening_promotion_test_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    session_id: str,
    answers: dict[str, int],
) -> PromotionTestSubmitOut:
    if not session_id.strip():
        raise PromotionTestApiError(400, "session_id is required")
    if not answers:
        raise PromotionTestApiError(400, "answers are required")

    state = await load_promotion_test_state(db, student_id=student_id, language_id=language_id)
    if _attempt_for_session(state, session_id):
        raise PromotionTestApiError(
            409,
            {"session_id": session_id, "reason": "Promotion test session already submitted."},
        )

    live = await get_session(
        db,
        session_id,
        student_id=student_id,
        language_id=language_id,
    )
    if live is None:
        status = await inspect_promotion_test_session(
            db,
            session_id,
            student_id=student_id,
            language_id=language_id,
        )
        if status == "wrong_owner":
            raise PromotionTestApiError(
                404,
                {"session_id": session_id, "reason": "Promotion test session not found."},
            )
        if status == "expired":
            raise PromotionTestApiError(
                410,
                {"session_id": session_id, "reason": "Promotion test session expired."},
            )
        raise PromotionTestApiError(
            404,
            {"session_id": session_id, "reason": "Promotion test session not found."},
        )

    if live.student_id != student_id or live.language_id != language_id:
        raise PromotionTestApiError(
            404,
            {"session_id": session_id, "reason": "Promotion test session not found."},
        )

    if time.time() > live.expires_at:
        raise PromotionTestApiError(
            410,
            {"session_id": session_id, "reason": "Promotion test session expired."},
        )

    normalized_answers: dict[str, int] = {}
    for key, value in answers.items():
        if not str(key).strip():
            raise PromotionTestApiError(400, "answer keys must be non-empty")
        if not isinstance(value, int):
            raise PromotionTestApiError(400, "answer values must be integers")
        normalized_answers[str(key)] = value

    result = await submit_listening_promotion_test(
        db,
        student_id=student_id,
        language_id=language_id,
        session_id=session_id,
        answers=normalized_answers,
    )
    if result is None:
        state = await load_promotion_test_state(db, student_id=student_id, language_id=language_id)
        if _attempt_for_session(state, session_id):
            raise PromotionTestApiError(
                409,
                {"session_id": session_id, "reason": "Promotion test session already submitted."},
            )
        raise PromotionTestApiError(
            404,
            {"session_id": session_id, "reason": "Promotion test session not found."},
        )
    return _result_to_submit_out(result)
