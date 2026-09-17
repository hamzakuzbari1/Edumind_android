"""Daily mission — a smart, personalized "what should I do today?".

Rule-based (no AI/quota). Blends the learner's weakest skill, due spaced-repetition reviews,
un-mastered curriculum objectives, and a conversation/scenario into a short daily mission, then
tracks live completion from today's activity log so the UI can show progress toward the goal.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.engagement import LanguageActivityLog
from app.services.language_curriculum_service import build_curriculum_overview
from app.services.language_subscription_service import get_default_language
from app.services.language_vocabulary_sr_service import count_due

SKILL_LABELS = {
    "reading": "Reading",
    "listening": "Listening",
    "writing": "Writing",
    "speaking": "Speaking",
}

# An activity-log event that marks a mission item (by feature) as done for today.
FEATURE_DONE_EVENTS = {
    "vocabulary": ("vocabulary_reviewed",),
    "reading": ("reading_lesson_completed",),
    "listening": ("listening_lesson_completed",),
    "writing": ("writing_completed",),
    "speaking": ("speaking_completed",),
    "conversation": ("speaking_conversation_turn",),
    "shadowing": ("shadowing_attempt",),
}


async def _today_events(db: AsyncSession, *, student_id: int, language_id: int) -> set[str]:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = await db.execute(
        select(LanguageActivityLog.event_type).where(
            LanguageActivityLog.student_id == student_id,
            LanguageActivityLog.language_id == language_id,
            LanguageActivityLog.created_at >= start,
        )
    )
    return {e for (e,) in rows.all() if e}


def _done(feature: str, today: set[str]) -> bool:
    return any(ev in today for ev in FEATURE_DONE_EVENTS.get(feature, ()))


async def build_daily_plan(db: AsyncSession, *, student_id: int) -> dict:
    overview = await build_curriculum_overview(db, student_id=student_id)
    objectives = overview.get("objectives") or []
    # In-progress objectives first (closest to mastery), then new ones.
    unmastered = [o for o in objectives if o.get("status") != "mastered"]
    unmastered.sort(key=lambda o: 0 if o.get("status") == "in_progress" else 1)

    language = await get_default_language(db)
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language.id})
    today = await _today_events(db, student_id=student_id, language_id=language.id)
    due_vocab = await count_due(db, student_id=student_id, language_id=language.id)

    items: list[dict] = []

    # 1) Spaced-repetition review when words are due — highest retention value.
    if due_vocab > 0:
        items.append(
            {
                "kind": "vocabulary",
                "title": f"Review {due_vocab} due word{'s' if due_vocab != 1 else ''}",
                "detail": "Spaced repetition keeps vocabulary from fading.",
                "feature": "vocabulary",
                "focus": None,
                "objective_id": None,
                "done": _done("vocabulary", today),
            }
        )

    # 2) Targeted work on the weakest skill.
    weak = (analytics.primary_focus_skill if analytics else None) or None
    if weak in SKILL_LABELS:
        items.append(
            {
                "kind": "skill",
                "title": f"Strengthen your {SKILL_LABELS[weak]}",
                "detail": "Your weakest skill right now — a little focus goes a long way.",
                "feature": weak,
                "focus": None,
                "objective_id": None,
                "done": _done(weak, today),
            }
        )

    # 3) One or two un-mastered objectives from the current level.
    for o in unmastered[:2]:
        focus = f"{o['title']} ({o['grammar']})" if o.get("grammar") else o["title"]
        items.append(
            {
                "kind": "objective",
                "title": f"Practice: {o['title']}",
                "detail": o.get("grammar") or o.get("vocab") or None,
                "feature": o.get("feature") or "conversation",
                "focus": focus,
                "objective_id": o["id"],
                "done": o.get("status") == "mastered" or _done(o.get("feature") or "", today),
            }
        )

    # 4) Always end with a live conversation (or role-play scenario).
    items.append(
        {
            "kind": "conversation",
            "title": "Have a short English conversation",
            "detail": "Put it all together by speaking.",
            "feature": "conversation",
            "focus": None,
            "objective_id": None,
            "done": _done("conversation", today),
        }
    )

    items = items[:5]
    completed_today = sum(1 for it in items if it["done"])
    return {
        "current_level": overview.get("current_level"),
        "mastery_progress_percent": overview.get("mastery_progress_percent", 0),
        "objectives_mastered": overview.get("objectives_mastered", 0),
        "objectives_total": overview.get("objectives_total", 0),
        "goal": len(items),
        "completed_today": completed_today,
        "due_vocab": due_vocab,
        "items": items,
    }
