"""Promotion test history persistence (Phase 5.4).

Stores attempts in promotion_readiness_json — never Official CEFR columns.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.progression import LanguageProgression
from app.services.language_listening_progression.json_mutation import mutate_listening_progression_json
from app.services.language_progression_service import record_progression_event
from app.services.language_promotion_test.types import PromotionTestResult, PromotionTestSession


def _tests_bucket(payload: dict) -> dict:
    bucket = payload.get("listening_promotion_tests")
    if not isinstance(bucket, dict):
        bucket = {"attempts": [], "used_lesson_ids": [], "used_sequences": []}
    bucket.setdefault("attempts", [])
    bucket.setdefault("used_lesson_ids", [])
    bucket.setdefault("used_sequences", [])
    return bucket


async def load_promotion_test_state(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> dict:
    row = await db.get(LanguageProgression, {"student_id": student_id, "language_id": language_id})
    if row is None or not row.promotion_readiness_json:
        return {"attempts": [], "used_lesson_ids": [], "used_sequences": []}
    payload = dict(row.promotion_readiness_json)
    return _tests_bucket(payload)


async def save_promotion_test_attempt(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    session: PromotionTestSession,
    result: PromotionTestResult,
    row: LanguageProgression | None = None,
) -> LanguageProgression | None:
    def mutator(payload: dict) -> bool:
        bucket = _tests_bucket(payload)
        for attempt in bucket.get("attempts") or []:
            if isinstance(attempt, dict) and str(attempt.get("session_id")) == result.session_id:
                return False

        attempt_record = {
            "session_id": result.session_id,
            "attempt_number": result.telemetry.attempt_number,
            "official_cefr": result.telemetry.official_cefr,
            "target_cefr": result.telemetry.target_cefr,
            "overall_score": result.overall_score,
            "result": result.result.value,
            "objective_scores": result.objective_scores,
            "evidence_score": result.score_breakdown.evidence_score,
            "consistency_score": result.score_breakdown.consistency_score,
            "coverage_score": result.score_breakdown.coverage_score,
            "exam_confidence": result.score_breakdown.exam_confidence,
            "lesson_ids": list(result.telemetry.lesson_ids),
            "objective_sequence": list(result.telemetry.objective_coverage),
            "strengths": list(result.strengths),
            "weaknesses": list(result.weaknesses),
            "recommendation": result.recommendation,
        }
        bucket["attempts"] = (bucket.get("attempts") or [])[-23:] + [attempt_record]
        bucket["used_lesson_ids"] = list(
            set(bucket.get("used_lesson_ids") or []) | set(session.lesson_ids)
        )[-200:]
        existing_sequences = {
            tuple(seq) for seq in (bucket.get("used_sequences") or []) if isinstance(seq, (list, tuple))
        }
        bucket["used_sequences"] = [
            list(seq) for seq in (existing_sequences | {tuple(session.objective_sequence)})
        ][-50:]
        bucket["last_session_id"] = session.session_id
        payload["listening_promotion_tests"] = bucket
        return True

    saved_row, inserted = await mutate_listening_progression_json(
        db,
        student_id=student_id,
        language_id=language_id,
        mutator=mutator,
        locked_row=row,
    )
    if saved_row is None or not inserted:
        return saved_row

    await record_progression_event(
        db,
        student_id=student_id,
        language_id=language_id,
        event_type="listening_promotion_test_completed",
        payload_json={
            "session_id": result.session_id,
            "attempt_number": result.telemetry.attempt_number,
            "result": result.result.value,
            "overall_score": result.overall_score,
            "official_cefr": result.telemetry.official_cefr,
            "target_cefr": result.telemetry.target_cefr,
        },
        force=True,
    )
    return saved_row
