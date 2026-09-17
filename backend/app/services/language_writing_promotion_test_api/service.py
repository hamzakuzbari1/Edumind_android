"""API orchestration for the Writing Promotion Assessment (WPA)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.language_writing_promotion_test import (
    WritingPromotionActiveSessionOut,
    WritingPromotionAttemptSummaryOut,
    WritingPromotionEligibilityOut,
    WritingPromotionLatestResultOut,
    WritingPromotionReadinessOut,
    WritingPromotionStabilityOut,
    WritingPromotionStartOut,
    WritingPromotionStatusOut,
    WritingPromotionSubmitOut,
    WritingPromotionTaskOut,
    WritingPromotionTaskResultOut,
)
from app.services.language_learner_memory_service import get_memory
from app.services.language_learning_facts.journey_assembler import resolve_personal_goal_from_memory
from app.services.language_learning_goal.types import LearningGoal
from app.services.language_progression_service import PROGRESSION_UNAVAILABLE_REASON, ensure_progression_row
from app.services.language_promotion_readiness.types import ReadinessStatus
from app.services.language_writing.enums import WritingGoal
from app.services.language_writing_promotion_readiness import evaluate_writing_promotion_readiness
from app.services.language_writing_promotion_stability import evaluate_writing_promotion_stability
from app.services.language_writing_promotion_test import (
    check_writing_promotion_test_eligibility,
    create_writing_promotion_test_session,
    submit_writing_promotion_test,
)
from app.services.language_writing_promotion_test.storage import get_active_session, latest_attempt, tests_bucket
from app.services.language_writing_runtime.student_context import official_writing_cefr_for_student


class WritingPromotionTestApiError(Exception):
    def __init__(self, status_code: int, detail: dict | str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


def _writing_goal_from_memory(memory: dict | None) -> WritingGoal:
    personal = resolve_personal_goal_from_memory(
        learning_goals=memory.get("learning_goals") if memory else None,
        future_goal=memory.get("future_goal") if memory else None,
    )
    try:
        return WritingGoal(personal.value)
    except ValueError:
        return WritingGoal.general_english


def _next_cefr(official: str) -> str:
    from app.models.language.enums import LanguageLevel
    from app.services.language_level_utils import CEFR_RANK, RANK_CEFR

    try:
        rank = CEFR_RANK.get(LanguageLevel(official.upper()), 1) + 1
        return RANK_CEFR[rank].value if rank in RANK_CEFR else official
    except ValueError:
        return official


def _session_start_out(session: dict) -> WritingPromotionStartOut:
    tasks = [
        WritingPromotionTaskOut(
            task_id=str(t.get("task_id", "")),
            task_type=str(t.get("task_type", "")),
            genre=str(t.get("genre", "")),
            prompt=str(t.get("prompt", "")),
            min_words=int(t.get("min_words") or 0),
            max_words=int(t.get("max_words") or 0),
            time_limit_minutes=int(t.get("time_limit_minutes") or 0),
        )
        for t in (session.get("tasks") or [])
        if isinstance(t, dict)
    ]
    return WritingPromotionStartOut(
        session_id=str(session.get("session_id", "")),
        official_cefr=str(session.get("official_cefr", "")),
        target_cefr=str(session.get("target_cefr", "")),
        goal=str(session.get("goal", "")),
        tasks=tasks,
    )


async def get_writing_promotion_test_status(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> WritingPromotionStatusOut:
    official = await official_writing_cefr_for_student(db, student_id=student_id, language_id=language_id)
    eligible, reason, score, target = await check_writing_promotion_test_eligibility(
        db, student_id=student_id, language_id=language_id
    )
    readiness = await evaluate_writing_promotion_readiness(
        db, student_id=student_id, language_id=language_id, official_cefr=official.value
    )
    stability = await evaluate_writing_promotion_stability(db, student_id=student_id, language_id=language_id)
    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {}) if row else {}
    active_raw = get_active_session(payload)
    last_raw = latest_attempt(payload)

    active = None
    if active_raw:
        active = WritingPromotionActiveSessionOut(
            session_id=str(active_raw.get("session_id", "")),
            official_cefr=str(active_raw.get("official_cefr", "")),
            target_cefr=str(active_raw.get("target_cefr", "")),
            goal=str(active_raw.get("goal", "")),
            task_count=len(active_raw.get("tasks") or []),
        )

    last_attempt = None
    latest_result = None
    if isinstance(last_raw, dict):
        last_attempt = WritingPromotionAttemptSummaryOut(
            session_id=str(last_raw.get("session_id", "")),
            official_cefr=str(last_raw.get("official_cefr", "")),
            target_cefr=str(last_raw.get("target_cefr", "")),
            overall_score=float(last_raw.get("overall_score", 0.0)),
            result=str(last_raw.get("result", "")),
        )
        latest_result = WritingPromotionLatestResultOut(
            session_id=last_attempt.session_id,
            overall_score=last_attempt.overall_score,
            result=last_attempt.result,
        )

    return WritingPromotionStatusOut(
        eligibility=WritingPromotionEligibilityOut(
            eligible=eligible,
            reason=reason,
            official_cefr=official.value,
            target_cefr=target,
            readiness_score=score,
            readiness_status=readiness.status.value,
        ),
        readiness=WritingPromotionReadinessOut(
            official_cefr=official.value,
            readiness_score=readiness.readiness_score,
            status=readiness.status.value,
            estimated_remaining=readiness.estimated_remaining,
            primary_blockers=list(readiness.primary_blockers),
        ),
        stability=WritingPromotionStabilityOut(
            promotion_confidence=stability.promotion_confidence,
            readiness_stability=stability.readiness_stability,
            prediction=stability.prediction,
        ),
        active_session=active,
        last_attempt=last_attempt,
        latest_result=latest_result,
    )


async def start_writing_promotion_test(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> WritingPromotionStartOut:
    if await ensure_progression_row(db, student_id=student_id, language_id=language_id) is None:
        raise WritingPromotionTestApiError(
            503,
            {
                "eligible": False,
                "reason": PROGRESSION_UNAVAILABLE_REASON,
                "progression_available": False,
            },
        )

    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {}) if row else {}
    existing = get_active_session(payload)
    if existing:
        return _session_start_out(existing)

    memory = await get_memory(db, student_id=student_id, language_id=language_id)
    goal = _writing_goal_from_memory(memory)
    created = await create_writing_promotion_test_session(
        db, student_id=student_id, language_id=language_id, goal=goal
    )
    if not created.get("eligible"):
        readiness = await evaluate_writing_promotion_readiness(db, student_id=student_id, language_id=language_id)
        raise WritingPromotionTestApiError(
            403,
            {
                "eligible": False,
                "reason": created.get("reason", "Not eligible for WPA."),
                "readiness_score": created.get("readiness_score", readiness.readiness_score),
                "readiness_status": readiness.status.value,
            },
        )
    session = created.get("session")
    if not isinstance(session, dict):
        raise WritingPromotionTestApiError(500, "Failed to create WPA session.")
    return _session_start_out(session)


async def submit_writing_promotion_test_api(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    session_id: str,
    submissions: dict[str, str],
) -> WritingPromotionSubmitOut:
    if not session_id.strip():
        raise WritingPromotionTestApiError(400, "session_id is required")
    if not submissions:
        raise WritingPromotionTestApiError(400, "submissions are required")

    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    payload = dict(row.promotion_readiness_json or {}) if row else {}
    for attempt in tests_bucket(payload).get("attempts") or []:
        if isinstance(attempt, dict) and str(attempt.get("session_id")) == session_id:
            raise WritingPromotionTestApiError(
                409,
                {"session_id": session_id, "reason": "WPA session already submitted."},
            )

    active = get_active_session(payload)
    if not active or str(active.get("session_id")) != session_id:
        raise WritingPromotionTestApiError(
            404,
            {"session_id": session_id, "reason": "WPA session not found."},
        )

    normalized: dict[str, str] = {}
    for key, value in submissions.items():
        if not str(key).strip():
            raise WritingPromotionTestApiError(400, "submission keys must be non-empty")
        normalized[str(key)] = str(value or "")

    result = await submit_writing_promotion_test(
        db,
        student_id=student_id,
        language_id=language_id,
        session_id=session_id,
        submissions=normalized,
    )
    if result is None:
        raise WritingPromotionTestApiError(
            404,
            {"session_id": session_id, "reason": "WPA session not found."},
        )

    task_results = [
        WritingPromotionTaskResultOut(
            task_id=tr.task_id,
            word_count=tr.word_count,
            passed=tr.passed,
            score=round(float(tr.criterion_scores.get("overall", 0.0)) * 100, 1),
        )
        for tr in result.task_results
    ]
    overall = round(sum(tr.score for tr in task_results) / len(task_results), 1) if task_results else 0.0
    return WritingPromotionSubmitOut(
        session_id=result.session_id,
        overall_score=overall,
        result=result.status.value.upper(),
        overall_passed=result.overall_passed,
        task_results=task_results,
    )
