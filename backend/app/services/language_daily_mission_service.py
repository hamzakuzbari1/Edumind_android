"""Phase 5 (extension) — Adaptive, renewable daily mission.

Builds ON TOP of the existing rule-based `build_daily_plan` (no AI/quota), adding:
  - Adaptive injection: each task is tagged with the learner's effective level (Phase 3) and the
    weakest task carries a reason drawn from recurring mistakes (Phase 2).
  - Renewal: once the day's mission is finished the learner can renew it for a fresh round.
  - Integrity: renewed rounds award a DIMINISHING XP multiplier (1.0 -> 0.5 -> 0.25 -> 0.1) and use
    round-scoped XP keys, so the mission can't be farmed by refreshing.

Round state is stored additively in `LanguageAnalytics.xp_keys_json["mission"]` = {date, round, base}.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.engagement import LanguageActivityLog
from app.services import language_difficulty_service as difficulty_service
from app.services import language_error_intelligence_service as error_service
from app.services.language_daily_plan_service import FEATURE_DONE_EVENTS, build_daily_plan
from app.services.language_subscription_service import get_default_language

# Diminishing XP multiplier per round (index = round-1); floor for any further round.
ROUND_MULTIPLIERS = (1.0, 0.5, 0.25, 0.1)
# Every qualifying activity event that can count toward a mission round.
ALL_MISSION_EVENTS = {ev for evs in FEATURE_DONE_EVENTS.values() for ev in evs}


# --------------------------------------------------------------------------------------------------
# Pure helpers (no I/O — unit-tested directly)
# --------------------------------------------------------------------------------------------------
def round_multiplier(round_num: int) -> float:
    """XP multiplier for a mission round (1.0 for round 1, diminishing after, floor at the last)."""
    if round_num < 1:
        round_num = 1
    idx = min(round_num - 1, len(ROUND_MULTIPLIERS) - 1)
    return ROUND_MULTIPLIERS[idx]


def mark_done_sequentially(items: list[dict], progress: int) -> list[dict]:
    """Mark the first `progress` items done (count-based completion for renewed rounds)."""
    progress = max(0, int(progress))
    for i, it in enumerate(items):
        it["done"] = i < progress
    return items


def read_state(analytics: LanguageAnalytics | None, today: str) -> dict:
    """Current round state for today (resets to round 1 / base 0 on a new day)."""
    store = (analytics.xp_keys_json or {}) if analytics else {}
    state = store.get("mission") if isinstance(store, dict) else None
    if not isinstance(state, dict) or state.get("date") != today:
        return {"date": today, "round": 1, "base": 0}
    return {"date": today, "round": int(state.get("round") or 1), "base": int(state.get("base") or 0)}


# --------------------------------------------------------------------------------------------------
# Persistence + orchestration
# --------------------------------------------------------------------------------------------------
async def _qualifying_event_count(db: AsyncSession, *, student_id: int, language_id: int) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = (
        await db.execute(
            select(func.count())
            .select_from(LanguageActivityLog)
            .where(
                LanguageActivityLog.student_id == student_id,
                LanguageActivityLog.language_id == language_id,
                LanguageActivityLog.created_at >= start,
                LanguageActivityLog.event_type.in_(ALL_MISSION_EVENTS),
            )
        )
    ).scalar_one()
    return int(total or 0)


async def _enrich(db: AsyncSession, *, student_id: int, language_id: int, items: list[dict]) -> str | None:
    """Tag each item with its effective level (Phase 3); add a recurring-mistake reason to the weakest
    task (Phase 2). Returns the overall effective level."""
    profile = await difficulty_service.calculate_modifier(db, student_id=student_id, language_id=language_id)
    overall = profile.get("effective_level") or profile.get("cefr_level")
    modifiers = profile.get("modifiers") or {}
    base_cefr = profile.get("cefr_level") or "A1"
    for it in items:
        feat = it.get("feature")
        if feat in difficulty_service.SKILL_DIMS:
            it["level"] = difficulty_service.effective_label(base_cefr, modifiers.get(feat, 0.0))
        else:
            it["level"] = overall

    recurring = await error_service.top_issue_labels(db, student_id=student_id, language_id=language_id)
    if recurring:
        # Attach to the weakest-skill task if present, else the first task.
        target = next((it for it in items if it.get("kind") == "skill"), items[0] if items else None)
        if target is not None:
            target["reason"] = f"You've slipped on this a few times: {recurring[0]}"
            target["adaptive"] = True
    return overall


async def build_daily_mission(db: AsyncSession, *, student_id: int) -> dict:
    """The daily plan, enriched + round-aware (adaptive, renewable, integrity-bounded XP)."""
    plan = await build_daily_plan(db, student_id=student_id)
    language = await get_default_language(db)
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language.id})
    today = datetime.now(timezone.utc).date().isoformat()
    state = read_state(analytics, today)
    rnd = state["round"]

    items = plan.get("items") or []
    coach_message = await _enrich(db, student_id=student_id, language_id=language.id, items=items)
    goal = int(plan.get("goal") or len(items))

    if rnd > 1:
        # Renewed (bonus) round: completion is counted from the round's baseline event count.
        total = await _qualifying_event_count(db, student_id=student_id, language_id=language.id)
        progress = min(goal, max(0, total - state["base"]))
        mark_done_sequentially(items, progress)
        plan["completed_today"] = progress

    completed = int(plan.get("completed_today") or 0)
    plan.update(
        items=items,
        round=rnd,
        xp_multiplier=round_multiplier(rnd),
        renewable=goal > 0 and completed >= goal,
        bonus=rnd > 1,
        coach_message=(f"Effective level: {coach_message}" if coach_message else None),
    )
    return plan


async def renew_daily_mission(db: AsyncSession, *, student_id: int) -> dict:
    """Start a fresh mission round — only when the current one is finished. Reduced XP afterwards."""
    mission = await build_daily_mission(db, student_id=student_id)
    if not mission.get("renewable"):
        return {"renewed": False, "reason": "Finish your current mission first.", "round": mission.get("round", 1)}

    language = await get_default_language(db)
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language.id})
    if analytics is None:
        analytics = LanguageAnalytics(student_id=student_id, language_id=language.id)
        db.add(analytics)
        await db.flush()

    today = datetime.now(timezone.utc).date().isoformat()
    new_round = int(mission.get("round", 1)) + 1
    base = await _qualifying_event_count(db, student_id=student_id, language_id=language.id)
    store = dict(analytics.xp_keys_json or {})
    store["mission"] = {"date": today, "round": new_round, "base": base}
    analytics.xp_keys_json = store  # reassign so SQLAlchemy tracks the JSONB change
    await db.flush()
    return {"renewed": True, "round": new_round, "xp_multiplier": round_multiplier(new_round)}
