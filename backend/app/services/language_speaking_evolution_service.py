"""Long-term speaking level evolution from placement + conversation turns."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.language.analytics import LanguageAnalytics
from app.models.language.assessment import LanguageAssessment, LanguageAssessmentSkillScore
from app.models.language.conversation import LanguageSpeakingConversationSession, LanguageSpeakingConversationTurn
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR, bottleneck_level, primary_focus_and_strength
from app.services.language_subscription_service import get_default_language

settings = get_settings()


def _conversation_turns_only():
    """Filter: only free-chat conversation turns — exclude role-play scenario turns.

    Scenario turns live in the same table (sessions with scenario_id set); they must NOT
    influence the conversation speaking level/progress.
    """
    return LanguageSpeakingConversationTurn.session_id.in_(
        select(LanguageSpeakingConversationSession.id).where(
            LanguageSpeakingConversationSession.scenario_id.is_(None)
        )
    )


def _parse_level(value: str | LanguageLevel | None) -> LanguageLevel | None:
    if value is None:
        return None
    if isinstance(value, LanguageLevel):
        return value
    try:
        return LanguageLevel(value.upper())
    except ValueError:
        return None


async def _placement_speaking_level(db: AsyncSession, *, student_id: int, language_id: int) -> LanguageLevel | None:
    result = await db.execute(
        select(LanguageAssessmentSkillScore.level)
        .join(LanguageAssessment, LanguageAssessment.id == LanguageAssessmentSkillScore.assessment_id)
        .where(
            LanguageAssessment.student_id == student_id,
            LanguageAssessment.language_id == language_id,
            LanguageAssessmentSkillScore.skill == LanguageSkill.speaking,
        )
        .order_by(desc(LanguageAssessment.completed_at))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return _parse_level(row)


async def _rolling_turn_levels(
    db: AsyncSession,
    *,
    student_id: int,
    window: int,
) -> list[int]:
    result = await db.execute(
        select(LanguageSpeakingConversationTurn.estimated_cefr)
        .where(
            LanguageSpeakingConversationTurn.student_id == student_id,
            _conversation_turns_only(),
        )
        .order_by(desc(LanguageSpeakingConversationTurn.created_at))
        .limit(window)
    )
    ranks = []
    for lv in result.scalars().all():
        parsed = _parse_level(lv)
        if parsed:
            ranks.append(CEFR_RANK[parsed])
    return ranks


def _weighted_median_rank(ranks: list[int]) -> int | None:
    if not ranks:
        return None
    return sorted(ranks)[len(ranks) // 2]


def _blend_level(
    *,
    placement: LanguageLevel | None,
    rolling_rank: int | None,
    current: LanguageLevel | None,
    turn_count: int,
) -> LanguageLevel | None:
    if rolling_rank is None and placement is None:
        return current
    if rolling_rank is None:
        return placement
    if placement is None:
        return RANK_CEFR.get(rolling_rank)

    placement_rank = CEFR_RANK[placement]
    # Weight conversation more as turn count grows (max 70% conversation weight)
    conv_weight = min(0.7, turn_count / max(turn_count + 10, 1))
    blended = round(placement_rank * (1 - conv_weight) + rolling_rank * conv_weight)
    blended = max(1, min(6, blended))

    # Cap movement to ±1 from current effective level per update when current exists
    if current:
        cur_rank = CEFR_RANK[current]
        if blended > cur_rank + 1:
            blended = cur_rank + 1
        elif blended < cur_rank - 1:
            blended = cur_rank - 1

    return RANK_CEFR.get(blended)


async def update_speaking_level_from_conversation(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> tuple[LanguageLevel | None, bool]:
    """Recompute speaking_level; returns (new_level, changed)."""
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if not analytics:
        analytics = LanguageAnalytics(student_id=student_id, language_id=language_id)
        db.add(analytics)
        await db.flush()

    turn_count_q = await db.execute(
        select(func.count())
        .select_from(LanguageSpeakingConversationTurn)
        .where(
            LanguageSpeakingConversationTurn.student_id == student_id,
            _conversation_turns_only(),
        )
    )
    turn_count = int(turn_count_q.scalar() or 0)

    placement = await _placement_speaking_level(db, student_id=student_id, language_id=language_id)

    # --- Mastery-gated progression ---------------------------------------------------
    # Take the recent window of turns; a turn's mastery score is the mean of its 4 scores.
    window = max(1, int(settings.LANGUAGE_MASTERY_WINDOW))
    promote_at = max(1, int(settings.LANGUAGE_MASTERY_PROMOTE))
    demote_at = int(settings.LANGUAGE_MASTERY_DEMOTE)

    recent = await db.execute(
        select(LanguageSpeakingConversationTurn.evaluation_json)
        .where(
            LanguageSpeakingConversationTurn.student_id == student_id,
            _conversation_turns_only(),
        )
        .order_by(desc(LanguageSpeakingConversationTurn.created_at))
        .limit(window)
    )
    score_sums = {"fluency": 0, "grammar": 0, "vocabulary": 0, "confidence": 0}
    score_n = 0
    mastery_scores: list[float] = []
    for ev in recent.scalars().all():
        scores = (ev or {}).get("scores") or {}
        if not scores:
            continue
        score_n += 1
        turn_vals = []
        for k in score_sums:
            v = int(scores.get(k) or 0)
            score_sums[k] += v
            turn_vals.append(v)
        mastery_scores.append(sum(turn_vals) / len(turn_vals))
    avg_scores = {k: round(v / score_n) if score_n else 0 for k, v in score_sums.items()}
    rolling_mastery = round(sum(mastery_scores) / len(mastery_scores)) if mastery_scores else 0
    turns_in_window = len(mastery_scores)

    previous = analytics.speaking_level or placement
    new_level = previous or LanguageLevel.A1
    # Only move levels once the window is full — proven, consistent performance, not luck.
    if previous and turns_in_window >= window:
        rank = CEFR_RANK[previous]
        if rolling_mastery >= promote_at and rank < 6:
            new_level = RANK_CEFR[rank + 1]          # mastered -> unlock next
        elif rolling_mastery < demote_at and rank > 1:
            new_level = RANK_CEFR[rank - 1]          # struggling -> ease difficulty
    changed = new_level != previous
    analytics.speaking_level = new_level

    cur_rank = CEFR_RANK[new_level]
    next_level = RANK_CEFR.get(cur_rank + 1) if cur_rank < 6 else None
    # Progress to mastering the current level: needs BOTH enough practice and a high rolling avg.
    practice_factor = min(1.0, turns_in_window / window)
    mastery_progress = round(min(100.0, (rolling_mastery / promote_at) * 100.0 * practice_factor))
    mastered = next_level is None or (turns_in_window >= window and rolling_mastery >= promote_at)

    growth = dict(analytics.skill_growth_json or {})
    speaking_growth = dict(growth.get("speaking") or {})
    speaking_growth["conversation"] = {
        "turns_total": turn_count,
        "average_scores": avg_scores,
        "effective_level": new_level.value,
        "placement_baseline": placement.value if placement else None,
        "rolling_mastery_score": rolling_mastery,
        "turns_in_window": turns_in_window,
        "mastery_window": window,
        "mastery_progress_percent": mastery_progress,
        "next_level": next_level.value if next_level else None,
        "mastered": mastered,
        "level_trend": "up" if changed and previous and CEFR_RANK[new_level] > CEFR_RANK[previous] else (
            "down" if changed and previous and CEFR_RANK[new_level] < CEFR_RANK[previous] else "stable"
        ),
    }
    growth["speaking"] = speaking_growth
    analytics.skill_growth_json = growth

    levels = {
        "reading": analytics.reading_level.value if analytics.reading_level else None,
        "listening": analytics.listening_level.value if analytics.listening_level else None,
        "writing": analytics.writing_level.value if analytics.writing_level else None,
        "speaking": analytics.speaking_level.value if analytics.speaking_level else None,
    }
    overall = bottleneck_level(levels)
    if overall:
        analytics.overall_level_internal = overall
    focus, strength = primary_focus_and_strength(levels)
    analytics.primary_focus_skill = focus
    analytics.strength_skill = strength
    await db.flush()
    return new_level, changed


async def build_conversation_progress(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int | None = None,
) -> dict:
    language = await get_default_language(db) if language_id is None else None
    lang_id = language_id or language.id
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": lang_id})

    placement = await _placement_speaking_level(db, student_id=student_id, language_id=lang_id)
    turn_count_q = await db.execute(
        select(func.count())
        .select_from(LanguageSpeakingConversationTurn)
        .where(
            LanguageSpeakingConversationTurn.student_id == student_id,
            _conversation_turns_only(),
        )
    )
    sessions_q = await db.execute(
        select(func.count())
        .select_from(LanguageSpeakingConversationSession)
        .where(
            LanguageSpeakingConversationSession.student_id == student_id,
            LanguageSpeakingConversationSession.language_id == lang_id,
            LanguageSpeakingConversationSession.status == "completed",
            LanguageSpeakingConversationSession.scenario_id.is_(None),
        )
    )
    last_q = await db.execute(
        select(LanguageSpeakingConversationTurn.created_at)
        .where(
            LanguageSpeakingConversationTurn.student_id == student_id,
            _conversation_turns_only(),
        )
        .order_by(desc(LanguageSpeakingConversationTurn.created_at))
        .limit(1)
    )

    conv_meta = {}
    if analytics and analytics.skill_growth_json:
        conv_meta = (analytics.skill_growth_json.get("speaking") or {}).get("conversation") or {}

    return {
        "effective_speaking_level": analytics.speaking_level.value if analytics and analytics.speaking_level else None,
        "placement_baseline_level": placement.value if placement else None,
        "conversation_turns_total": int(turn_count_q.scalar() or 0),
        "sessions_completed": int(sessions_q.scalar() or 0),
        "average_scores": conv_meta.get("average_scores") or {
            "fluency": 0,
            "grammar": 0,
            "vocabulary": 0,
            "confidence": 0,
        },
        "level_trend": conv_meta.get("level_trend"),
        "last_conversation_at": last_q.scalar_one_or_none(),
        "next_level": conv_meta.get("next_level"),
        "mastery_progress_percent": int(conv_meta.get("mastery_progress_percent") or 0),
        "rolling_mastery_score": int(conv_meta.get("rolling_mastery_score") or 0),
        "turns_in_window": int(conv_meta.get("turns_in_window") or 0),
        "mastery_window": int(conv_meta.get("mastery_window") or settings.LANGUAGE_MASTERY_WINDOW),
        "mastered": bool(conv_meta.get("mastered")),
    }
