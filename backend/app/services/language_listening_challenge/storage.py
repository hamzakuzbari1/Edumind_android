"""Challenge persistence via preferences_json (Phase 3.3)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.services.language_student_profile_service import (
    get_language_student_profile,
    get_or_create_language_student_profile,
)
from app.services.language_listening_challenge.constants import (
    CHALLENGE_KEY,
    DEFAULT_CHALLENGE,
    HISTORY_WINDOW,
)
from app.services.language_listening_challenge.types import (
    ChallengeLessonRecord,
    ChallengeLevel,
    ChallengeState,
)


def _record_from_dict(raw: dict) -> ChallengeLessonRecord:
    return ChallengeLessonRecord(
        lesson_index=int(raw.get("lesson_index", 0)),
        accuracy=float(raw.get("accuracy", 0.5)),
        passed=bool(raw.get("passed", False)),
        confidence_trend=float(raw.get("confidence_trend", 0.0)),
        evidence_growth=float(raw.get("evidence_growth", 0.0)),
        review_performance=float(raw.get("review_performance", 0.5)),
        was_review=bool(raw.get("was_review", False)),
        success_streak=int(raw.get("success_streak", 0)),
        failure_streak=int(raw.get("failure_streak", 0)),
        time_spent_sec=raw.get("time_spent_sec"),
        hint_count=int(raw.get("hint_count", 0)),
        retry_count=int(raw.get("retry_count", 0)),
        lesson_score=float(raw.get("lesson_score", 0.5)),
    )


def build_initial_challenge_state(level: str) -> ChallengeState:
    return ChallengeState(
        level=level,
        current_level=ChallengeLevel(DEFAULT_CHALLENGE),
        challenge_score=0.5,
    )


def load_challenge_state(raw: dict | None, *, level: str) -> ChallengeState:
    state = build_initial_challenge_state(level)
    if not isinstance(raw, dict):
        return state

    level_blob = raw.get(level) if isinstance(raw.get(level), dict) else raw
    if not isinstance(level_blob, dict):
        return state

    try:
        state.current_level = ChallengeLevel(str(level_blob.get("current_level", DEFAULT_CHALLENGE)))
    except ValueError:
        state.current_level = ChallengeLevel(DEFAULT_CHALLENGE)

    state.challenge_score = float(level_blob.get("challenge_score", 0.5))
    state.promotion_count = int(level_blob.get("promotion_count", 0))
    state.demotion_count = int(level_blob.get("demotion_count", 0))
    state.promote_streak = int(level_blob.get("promote_streak", 0))
    state.demote_streak = int(level_blob.get("demote_streak", 0))
    state.lesson_index = int(level_blob.get("lesson_index", 0))
    state.last_adjustment_reason = str(level_blob.get("last_adjustment_reason", "loaded"))

    hist = level_blob.get("history") or []
    if isinstance(hist, list):
        state.history = [
            _record_from_dict(item) for item in hist[-HISTORY_WINDOW:] if isinstance(item, dict)
        ]

    adj = level_blob.get("adjustment_history") or []
    if isinstance(adj, list):
        state.adjustment_history = [item for item in adj if isinstance(item, dict)]

    return state


def serialize_challenge_state(state: ChallengeState) -> dict[str, object]:
    return {state.level: state.to_dict()}


async def load_student_challenge(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level: str,
) -> ChallengeState:
    profile = await get_language_student_profile(
        db, student_id=student_id, language_id=language_id
    )
    if not profile or not isinstance(profile.preferences_json, dict):
        return build_initial_challenge_state(level)
    raw = profile.preferences_json.get(CHALLENGE_KEY)
    return load_challenge_state(raw if isinstance(raw, dict) else None, level=level)


async def save_student_challenge(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    state: ChallengeState,
) -> None:
    profile = await get_or_create_language_student_profile(
        db, student_id=student_id, language_id=language_id
    )
    prefs = dict(profile.preferences_json or {})
    existing = prefs.get(CHALLENGE_KEY)
    merged: dict[str, object] = dict(existing) if isinstance(existing, dict) else {}
    merged.update(serialize_challenge_state(state))
    prefs[CHALLENGE_KEY] = merged
    profile.preferences_json = prefs
    flag_modified(profile, "preferences_json")
