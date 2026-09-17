"""Collect student signals for Educational Case personalization (I/O layer)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import StudentProfile
from app.services.language_speaking_case_personalization.memory import case_memory_from_payload
from app.services.language_speaking_case_personalization.types import StudentCaseSignals
from app.services.language_speaking_knowledge_model.storage import (
    knowledge_model_from_speaking_bucket,
    speaking_bucket_from_payload,
)


def _parse_json_list(raw: str | list | None) -> list[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return [str(x).strip() for x in data if str(x).strip()]
    return []


def build_signals_from_parts(
    *,
    student_id: int = 0,
    age: int | None = None,
    occupation: str = "",
    future_goal: str = "",
    learning_style: str = "",
    explanation_style: str = "",
    interests: list[str] | tuple[str, ...] | None = None,
    hobbies: list[str] | tuple[str, ...] | None = None,
    favorite_topics: list[str] | tuple[str, ...] | None = None,
    avoided_topics: list[str] | tuple[str, ...] | None = None,
    weak_skill_labels: list[str] | tuple[str, ...] | None = None,
    recent_mistake_tags: list[str] | tuple[str, ...] | None = None,
    completed_case_titles: list[str] | tuple[str, ...] | None = None,
    used_settings: list[str] | tuple[str, ...] | None = None,
    used_theme_keys: list[str] | tuple[str, ...] | None = None,
    used_emotional_themes: list[str] | tuple[str, ...] | None = None,
    used_decision_patterns: list[str] | tuple[str, ...] | None = None,
    promotion_readiness_json: dict[str, Any] | None = None,
    culture_hint: str = "",
    locale: str = "en",
) -> StudentCaseSignals:
    """Pure builder for tests / verifiers — no DB."""
    ledger = case_memory_from_payload(promotion_readiness_json)
    return StudentCaseSignals(
        student_id=student_id,
        age=age,
        occupation=occupation or "",
        future_goal=future_goal or "",
        learning_style=learning_style or "",
        explanation_style=explanation_style or "",
        interests=tuple(interests or ()),
        hobbies=tuple(hobbies or ()),
        favorite_topics=tuple(favorite_topics or ()),
        avoided_topics=tuple(avoided_topics or ()),
        weak_skill_labels=tuple(weak_skill_labels or ()),
        recent_mistake_tags=tuple(recent_mistake_tags or ()),
        completed_case_titles=tuple(completed_case_titles or ledger.used_case_titles),
        used_settings=tuple(used_settings or ledger.used_settings),
        used_theme_keys=tuple(used_theme_keys or ledger.used_theme_keys),
        used_emotional_themes=tuple(used_emotional_themes or ledger.used_emotional_themes),
        used_decision_patterns=tuple(
            used_decision_patterns or ledger.used_decision_patterns
        ),
        culture_hint=culture_hint,
        locale=locale,
    )


async def collect_case_personalization_signals(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int = 1,
    promotion_readiness_json: dict[str, Any] | None = None,
    locale: str = "en",
) -> StudentCaseSignals:
    """Load existing student profile + speaking memory signals (no new schema)."""
    # Verifiers / unit tests may pass a stub session — stay best-effort.
    if db is None or not hasattr(db, "execute"):
        return build_signals_from_parts(
            student_id=student_id,
            promotion_readiness_json=promotion_readiness_json,
            locale=locale,
        )

    profile: StudentProfile | None = None
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == student_id)
    )
    profile = result.scalar_one_or_none()

    interests = _parse_json_list(profile.interests_json if profile else None)
    hobbies = _parse_json_list(profile.hobbies_json if profile else None)

    # Merge learner-memory interests when available (shared infrastructure)
    favorite_topics: list[str] = []
    avoided_topics: list[str] = []
    try:
        from app.services.language_learner_memory_service import get_memory

        memory = await get_memory(db, student_id=student_id, language_id=language_id)
        if isinstance(memory, dict):
            interests = list(
                dict.fromkeys(
                    interests
                    + [str(x) for x in (memory.get("interests") or []) if str(x).strip()]
                )
            )
            favorite_topics = [
                str(x) for x in (memory.get("favorite_topics") or []) if str(x).strip()
            ]
            # Optional writing-coach-style field if present in prefs
            avoided_topics = [
                str(x) for x in (memory.get("avoided_topics") or []) if str(x).strip()
            ]
    except Exception:  # noqa: BLE001 — personalization is best-effort
        pass

    weak_labels: list[str] = []
    mistake_tags: list[str] = []
    payload = promotion_readiness_json
    if payload is None:
        try:
            from app.services.language_progression_service import ensure_progression_row

            row = await ensure_progression_row(
                db, student_id=student_id, language_id=language_id
            )
            payload = dict(row.promotion_readiness_json or {}) if row else {}
        except Exception:  # noqa: BLE001
            payload = {}

    try:
        bucket = speaking_bucket_from_payload(payload)
        km = knowledge_model_from_speaking_bucket(
            bucket, student_id=student_id, language_id=language_id
        )
        skills = getattr(km, "skill_states", None) or {}
        if isinstance(skills, dict):
            for skill_id, state in skills.items():
                status = getattr(state, "current_status", None)
                status_v = status.value if hasattr(status, "value") else str(status or "")
                if status_v in {"at_risk", "developing"}:
                    label = str(skill_id).replace(":", " ").replace("_", " ")
                    weak_labels.append(label)
                tags = list(getattr(state, "recent_mistake_tags", ()) or ())
                for t in tags[:3]:
                    if t and str(t) not in mistake_tags:
                        mistake_tags.append(str(t))
        weak_labels = weak_labels[:6]
        mistake_tags = mistake_tags[:6]
    except Exception:  # noqa: BLE001
        pass

    future_goal = str(profile.future_goal or "") if profile else ""
    # Occupation is not a dedicated profile column; future_goal often carries career intent.
    occupation = future_goal if future_goal and future_goal.lower() not in {"undecided", ""} else ""

    return build_signals_from_parts(
        student_id=student_id,
        age=profile.age if profile else None,
        occupation=occupation,
        future_goal=future_goal,
        learning_style=str(profile.learning_style or "") if profile else "",
        explanation_style=str(profile.preferred_explanation_style or "") if profile else "",
        interests=interests,
        hobbies=hobbies,
        favorite_topics=favorite_topics,
        avoided_topics=avoided_topics,
        weak_skill_labels=weak_labels,
        recent_mistake_tags=mistake_tags,
        promotion_readiness_json=payload if isinstance(payload, dict) else {},
        culture_hint="arabic_levant" if str(locale).lower().startswith("ar") else "",
        locale=locale,
    )
