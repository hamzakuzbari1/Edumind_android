"""Persistent promotion test session storage in promotion_readiness_json (PR-C)."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.progression import LanguageProgression
from app.services.language_listening_progression.json_mutation import mutate_listening_progression_json
from app.services.language_promotion_test.storage import _tests_bucket
from app.services.language_promotion_test.types import PromotionAssessmentSpec, PromotionTestSession


def _assessment_to_dict(spec: PromotionAssessmentSpec) -> dict[str, Any]:
    return {
        "assessment_id": spec.assessment_id,
        "lesson_id": spec.lesson_id,
        "objective_id": spec.objective_id,
        "objective_label": spec.objective_label,
        "situation": spec.situation,
        "format": spec.format,
        "speaker_count": spec.speaker_count,
        "difficulty_band": spec.difficulty_band,
        "question": spec.question,
        "choices": list(spec.choices),
        "correct_index": spec.correct_index,
        "sequence_index": spec.sequence_index,
    }


def _assessment_from_dict(raw: dict[str, Any]) -> PromotionAssessmentSpec:
    return PromotionAssessmentSpec(
        assessment_id=str(raw.get("assessment_id", "")),
        lesson_id=str(raw.get("lesson_id", "")),
        objective_id=str(raw.get("objective_id", "")),
        objective_label=str(raw.get("objective_label", "")),
        situation=str(raw.get("situation", "")),
        format=str(raw.get("format", "")),
        speaker_count=int(raw.get("speaker_count") or 1),
        difficulty_band=str(raw.get("difficulty_band") or "normal"),
        question=str(raw.get("question", "")),
        choices=tuple(str(c) for c in (raw.get("choices") or [])),
        correct_index=int(raw.get("correct_index") or 0),
        sequence_index=int(raw.get("sequence_index") or 0),
    )


def session_to_dict(session: PromotionTestSession) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "student_id": session.student_id,
        "language_id": session.language_id,
        "official_cefr": session.official_cefr,
        "target_cefr": session.target_cefr,
        "attempt_number": session.attempt_number,
        "expires_at": session.expires_at,
        "objective_sequence": list(session.objective_sequence),
        "lesson_ids": list(session.lesson_ids),
        "assessments": [_assessment_to_dict(a) for a in session.assessments],
    }


def session_from_dict(raw: dict[str, Any]) -> PromotionTestSession:
    assessments = [
        _assessment_from_dict(item)
        for item in (raw.get("assessments") or [])
        if isinstance(item, dict)
    ]
    return PromotionTestSession(
        session_id=str(raw.get("session_id", "")),
        student_id=int(raw.get("student_id") or 0),
        language_id=int(raw.get("language_id") or 0),
        official_cefr=str(raw.get("official_cefr", "")),
        target_cefr=str(raw.get("target_cefr", "")),
        attempt_number=int(raw.get("attempt_number") or 1),
        assessments=assessments,
        expires_at=float(raw.get("expires_at") or 0),
        objective_sequence=tuple(str(o) for o in (raw.get("objective_sequence") or [])),
        lesson_ids=tuple(str(l) for l in (raw.get("lesson_ids") or [])),
    )


def _active_sessions_map(bucket: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = bucket.get("active_sessions")
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _prune_expired_sessions(bucket: dict[str, Any]) -> None:
    now = time.time()
    active = _active_sessions_map(bucket)
    kept = {
        sid: data
        for sid, data in active.items()
        if float(data.get("expires_at") or 0) > now
    }
    bucket["active_sessions"] = kept
    active_id = bucket.get("active_session_id")
    if active_id and str(active_id) not in kept:
        bucket["active_session_id"] = next(iter(kept), None)


def _find_valid_active_session(
    bucket: dict[str, Any],
    *,
    student_id: int,
    language_id: int,
) -> PromotionTestSession | None:
    now = time.time()
    active = _active_sessions_map(bucket)
    preferred = bucket.get("active_session_id")
    order: list[str] = []
    if preferred and str(preferred) in active:
        order.append(str(preferred))
    order.extend(sid for sid in active if sid not in order)

    for session_id in order:
        raw = active[session_id]
        if float(raw.get("expires_at") or 0) <= now:
            continue
        session = session_from_dict(raw)
        if session.student_id == student_id and session.language_id == language_id:
            return session
    return None


async def register_promotion_test_session(
    db: AsyncSession,
    session: PromotionTestSession,
    *,
    locked_row: LanguageProgression | None = None,
) -> PromotionTestSession:
    """Persist a new session or return an existing valid active session (no duplicates)."""

    def mutator(payload: dict) -> PromotionTestSession:
        bucket = _tests_bucket(payload)
        _prune_expired_sessions(bucket)
        existing = _find_valid_active_session(
            bucket, student_id=session.student_id, language_id=session.language_id
        )
        if existing is not None:
            return existing

        active = _active_sessions_map(bucket)
        active[session.session_id] = session_to_dict(session)
        bucket["active_sessions"] = active
        bucket["active_session_id"] = session.session_id
        payload["listening_promotion_tests"] = bucket
        return session

    row, result = await mutate_listening_progression_json(
        db,
        student_id=session.student_id,
        language_id=session.language_id,
        mutator=mutator,
        locked_row=locked_row,
    )
    if row is None or result is None:
        raise RuntimeError("Cannot persist promotion test session without a progression row.")
    return result


async def load_promotion_test_session(
    db: AsyncSession,
    *,
    session_id: str,
    student_id: int,
    language_id: int,
) -> PromotionTestSession | None:
    if not session_id.strip():
        return None

    row = await db.get(LanguageProgression, {"student_id": student_id, "language_id": language_id})
    if row is None:
        return None
    return _load_session_from_row(row, session_id, student_id=student_id, language_id=language_id)


def _load_session_from_row(
    row: LanguageProgression,
    session_id: str,
    *,
    student_id: int,
    language_id: int,
    ignore_expiry: bool = False,
) -> PromotionTestSession | None:
    payload = dict(row.promotion_readiness_json or {})
    bucket = _tests_bucket(payload)
    raw = _active_sessions_map(bucket).get(session_id)
    if raw is None:
        return None
    session = session_from_dict(raw)
    if session.student_id != student_id or session.language_id != language_id:
        return None
    if not ignore_expiry and time.time() > session.expires_at:
        return None
    return session


async def inspect_promotion_test_session(
    db: AsyncSession,
    session_id: str,
    *,
    student_id: int,
    language_id: int,
) -> str:
    """Return ok | not_found | wrong_owner | expired."""
    row = await db.get(LanguageProgression, {"student_id": student_id, "language_id": language_id})
    if row is None:
        return "not_found"
    payload = dict(row.promotion_readiness_json or {})
    bucket = _tests_bucket(payload)
    raw = _active_sessions_map(bucket).get(session_id)
    if raw is None:
        return "not_found"
    session = session_from_dict(raw)
    if session.student_id != student_id or session.language_id != language_id:
        return "wrong_owner"
    if time.time() > session.expires_at:
        return "expired"
    return "ok"


async def remove_promotion_test_session(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    session_id: str,
    locked_row: LanguageProgression | None = None,
) -> PromotionTestSession | None:
    def mutator(payload: dict) -> PromotionTestSession | None:
        bucket = _tests_bucket(payload)
        active = _active_sessions_map(bucket)
        raw = active.pop(session_id, None)
        if bucket.get("active_session_id") == session_id:
            bucket["active_session_id"] = next(iter(active), None)
        bucket["active_sessions"] = active
        payload["listening_promotion_tests"] = bucket
        if raw is None:
            return None
        return session_from_dict(raw)

    _row, result = await mutate_listening_progression_json(
        db,
        student_id=student_id,
        language_id=language_id,
        mutator=mutator,
        locked_row=locked_row,
    )
    return result


async def find_active_promotion_test_session(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> PromotionTestSession | None:
    row = await db.get(LanguageProgression, {"student_id": student_id, "language_id": language_id})
    if row is None:
        return None
    payload = dict(row.promotion_readiness_json or {})
    bucket = _tests_bucket(payload)
    return _find_valid_active_session(bucket, student_id=student_id, language_id=language_id)


async def clear_promotion_test_sessions(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> None:
    def mutator(payload: dict) -> None:
        bucket = _tests_bucket(payload)
        bucket["active_sessions"] = {}
        bucket["active_session_id"] = None
        payload["listening_promotion_tests"] = bucket

    await mutate_listening_progression_json(
        db,
        student_id=student_id,
        language_id=language_id,
        mutator=mutator,
    )


def attempt_exists_for_session(bucket: dict[str, Any], session_id: str) -> bool:
    for attempt in bucket.get("attempts") or []:
        if isinstance(attempt, dict) and str(attempt.get("session_id")) == session_id:
            return True
    return False
