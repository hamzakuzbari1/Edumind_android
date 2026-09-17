"""Language XP — the single progression engine.

XP is the gate: activities award XP, XP fills the current level's bar, and when the bar is
full the learner advances to the next CEFR level (all skills at/below the current level rise
together). You can never skip a level — you must earn the current level's XP first.

`award_language_xp` is idempotent per key (like the platform gamification XP), so repeatable
activities must pass a unique key (e.g. a turn id), one-off activities a stable key.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.enums import LanguageLevel
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR, bottleneck_level

# XP required to advance FROM each level to the next. C2 is the top (no further).
# Tuned so the first level-up takes ~8-10 activities and later levels scale up gradually.
LEVEL_XP_REQUIRED: dict[str, int] = {
    "A1": 250,
    "A2": 450,
    "B1": 700,
    "B2": 1000,
    "C1": 1300,
    "C2": 0,
}

# XP amounts per activity type.
#
# Progression model: repeatable/infinite activities (conversation, vocab review) do NOT award
# XP directly — they earn XP only through the DAILY MISSION (bounded ~5 tasks/day), so a learner
# can keep chatting freely for practice but can't farm XP. Finite content (lessons, objectives,
# scenarios) awards once each as milestones.
XP_AWARDS: dict[str, int] = {
    "lesson": 30,         # reading/listening lesson passed (once per lesson)
    "writing": 35,        # writing prompt passed (once per prompt)
    "speaking": 35,       # speaking exercise passed (once per prompt)
    "objective": 40,      # curriculum objective mastered (once per objective)
    "scenario": 60,       # role-play scenario completed (once per scenario)
    "daily_item": 25,     # one daily-mission task completed (bounded: ~5/day)
    "daily_goal": 50,     # whole daily mission completed (bonus, once/day)
}


def _current_level(analytics: LanguageAnalytics | None) -> LanguageLevel:
    if not analytics:
        return LanguageLevel.A1
    levels = {
        "reading": analytics.reading_level.value if analytics.reading_level else None,
        "listening": analytics.listening_level.value if analytics.listening_level else None,
        "writing": analytics.writing_level.value if analytics.writing_level else None,
        "speaking": analytics.speaking_level.value if analytics.speaking_level else None,
    }
    return analytics.overall_level_internal or bottleneck_level(levels) or LanguageLevel.A1


_SKILL_ATTRS = ("reading_level", "listening_level", "writing_level", "speaking_level")


def _advance_one_level(analytics: LanguageAnalytics) -> LanguageLevel | None:
    """Raise the single WEAKEST skill by one CEFR band and recompute the overall level.

    XP progression targets the weakest skill (which is also what the daily plan focuses on), so a
    learner gradually lifts their lagging skill instead of every skill snapping up at once — this
    preserves the per-skill granularity the placement exam established. Returns the new overall
    level, or None if every skill is already at C2.
    """
    def _rank(v: LanguageLevel | None) -> int:
        return CEFR_RANK.get(v, 1) if v else 1

    ranks = {attr: _rank(getattr(analytics, attr)) for attr in _SKILL_ATTRS}
    weakest = min(_SKILL_ATTRS, key=lambda a: ranks[a])
    if ranks[weakest] >= 6:
        return None
    setattr(analytics, weakest, RANK_CEFR[ranks[weakest] + 1])

    new_ranks = [_rank(getattr(analytics, attr)) for attr in _SKILL_ATTRS]
    analytics.overall_level_internal = RANK_CEFR[round(sum(new_ranks) / len(new_ranks))]
    return analytics.overall_level_internal


async def award_language_xp(
    db: AsyncSession, *, student_id: int, language_id: int, activity: str, key: str,
    amount: int | None = None,
) -> dict:
    """Award XP for an activity (idempotent per key) and auto-advance level(s) when the bar fills.

    `amount` overrides the default XP_AWARDS[activity] — used for reduced-reward renewed missions.
    """
    amount = XP_AWARDS.get(activity, 0) if amount is None else max(0, int(amount))
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics is None:
        analytics = LanguageAnalytics(student_id=student_id, language_id=language_id)
        db.add(analytics)
        await db.flush()

    store = dict(analytics.xp_keys_json or {})
    keys = set(store.get("k", []))
    if amount <= 0 or key in keys:
        return {"awarded": 0, "leveled_up": False, "new_level": None}

    keys.add(key)
    store["k"] = sorted(keys)
    analytics.xp_keys_json = store
    analytics.xp_total = int(analytics.xp_total or 0) + amount
    analytics.level_xp = int(analytics.level_xp or 0) + amount

    leveled_up = False
    new_level = None
    # Advance through as many levels as the accumulated XP allows.
    while True:
        current = _current_level(analytics)
        needed = LEVEL_XP_REQUIRED.get(current.value, 0)
        if needed <= 0 or analytics.level_xp < needed:
            break
        advanced = _advance_one_level(analytics)
        if not advanced:
            break
        analytics.level_xp -= needed
        leveled_up = True
        new_level = advanced.value

    await db.flush()
    return {"awarded": amount, "leveled_up": leveled_up, "new_level": new_level, "xp_total": analytics.xp_total}


def _reduced(base: int, multiplier: float) -> int:
    """Reduced reward for renewed mission rounds (integrity: less XP each renewal). >=1 if multiplier>0."""
    if multiplier >= 1.0:
        return base
    return max(1, round(base * multiplier)) if multiplier > 0 else 0


async def award_daily_mission_xp(db: AsyncSession, *, student_id: int, language_id: int, plan: dict) -> dict:
    """Grant XP for completed daily-mission tasks + a full-mission bonus.

    This is the ONLY XP path for repeatable activities (conversation, vocab review): the learner may
    keep practising freely, but XP is bounded per daily task. Renewed rounds (round > 1) award a
    REDUCED amount (plan["xp_multiplier"]) and use round-scoped keys, so refreshing the mission can't
    be used to farm XP — for integrity.
    """
    today = date.today().isoformat()
    items = plan.get("items") or []
    rnd = int(plan.get("round") or 1)
    multiplier = float(plan.get("xp_multiplier") or 1.0)
    item_xp = _reduced(XP_AWARDS["daily_item"], multiplier)
    goal_xp = _reduced(XP_AWARDS["daily_goal"], multiplier)

    total_awarded = 0
    leveled_up = False
    new_level = None
    for it in items:
        if not it.get("done"):
            continue
        # Stable, round-scoped key by task identity (kind+feature) — order-independent, so reordering
        # personalized items never re-awards XP.
        slot = f"{it.get('kind', '')}:{it.get('feature', '')}"
        res = await award_language_xp(
            db, student_id=student_id, language_id=language_id,
            activity="daily_item", key=f"daily:{today}:r{rnd}:{slot}", amount=item_xp,
        )
        total_awarded += res.get("awarded", 0)
        leveled_up = leveled_up or res.get("leveled_up", False)
        new_level = res.get("new_level") or new_level
    goal = int(plan.get("goal") or 0)
    if goal > 0 and int(plan.get("completed_today") or 0) >= goal:
        res = await award_language_xp(
            db, student_id=student_id, language_id=language_id,
            activity="daily_goal", key=f"dailygoal:{today}:r{rnd}", amount=goal_xp,
        )
        total_awarded += res.get("awarded", 0)
        leveled_up = leveled_up or res.get("leveled_up", False)
        new_level = res.get("new_level") or new_level
    return {"awarded": total_awarded, "leveled_up": leveled_up, "new_level": new_level}


async def get_xp_overview(db: AsyncSession, *, student_id: int, language_id: int) -> dict:
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    current = _current_level(analytics)
    needed = LEVEL_XP_REQUIRED.get(current.value, 0)
    level_xp = int(analytics.level_xp or 0) if analytics else 0
    cur_rank = CEFR_RANK.get(current, 1)
    next_level = RANK_CEFR.get(cur_rank + 1)
    percent = 100 if needed <= 0 else min(100, round(100 * level_xp / needed))
    return {
        "xp_total": int(analytics.xp_total or 0) if analytics else 0,
        "current_level": current.value,
        "next_level": next_level.value if next_level else None,
        "level_xp": level_xp,
        "xp_needed": needed,
        "percent_to_next": percent,
        "is_max_level": next_level is None,
    }
