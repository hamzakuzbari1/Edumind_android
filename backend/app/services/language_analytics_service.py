"""Roll up language_analytics — completion, vocabulary, skill growth (not CEFR promotion)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageContentProgressStatus, LanguageLevel, LanguageSkill, LanguageVocabularyStatus
from app.models.language.engagement import LanguageStreak
from app.models.language.progress import (
    LanguageListeningProgress,
    LanguageReadingProgress,
    LanguageSpeakingProgress,
    LanguageVocabularyProgress,
    LanguageWritingProgress,
)
from app.services.language_content_service import normalize_word, resolve_content_level
from app.services.language_level_utils import CEFR_RANK, bottleneck_level, primary_focus_and_strength
from app.services.language_subscription_service import get_default_language

GROWTH_COMPLETION_WEIGHT = 0.6
GROWTH_SCORE_WEIGHT = 0.4
# Reading/listening are now AI-generated and effectively infinite, so "% of all lessons completed"
# would collapse toward zero and never move. Measure completion against a fixed target instead, so
# finishing a handful of lessons fills the completion part.
GROWTH_TARGET_LESSONS = 8


def compute_growth_percent(*, lessons_completed: int, lessons_total: int, average_score: float | None) -> int:
    if lessons_total <= 0 and lessons_completed <= 0:
        return 0
    # Denominator is a fixed target (capped by how many lessons actually exist), not the full —
    # possibly unbounded — pool, so each completed lesson visibly advances growth.
    denom = min(lessons_total, GROWTH_TARGET_LESSONS) if lessons_total > 0 else GROWTH_TARGET_LESSONS
    completion_ratio = min(1.0, lessons_completed / denom) if denom > 0 else 0.0
    if average_score is None:
        # No score signal (e.g. speaking has no graded score column) — completion carries the full
        # weight, otherwise growth would be permanently capped at 60% and drag overall progress.
        return int(min(100, round(completion_ratio * 100.0)))
    completion_part = completion_ratio * 100.0 * GROWTH_COMPLETION_WEIGHT
    score_part = average_score * GROWTH_SCORE_WEIGHT
    return int(min(100, round(completion_part + score_part)))


async def _skill_growth_for_level(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill: LanguageSkill,
    level: LanguageLevel | None,
    progress_model: type,
    content_type: str = "lesson",
    completed_filter,
    score_column=None,
) -> dict:
    empty = {
        "level": level.value if level else None,
        "content_level": None,
        "growth_percent": 0,
        "lessons_completed": 0,
        "lessons_total": 0,
        "average_score_percent": None,
    }
    if not level:
        return empty

    # Count progress at-or-below the current level, not just the exact level. Reading/listening are
    # adaptive, so the level keeps moving; an exact-level count would RESET growth to ~0 every time
    # the learner is nudged up. Cumulative (≤ current) keeps growth monotonic and meaningful.
    max_rank = CEFR_RANK.get(level, 1)
    allowed_levels = [lv for lv, r in CEFR_RANK.items() if r <= max_rank]

    total_q = await db.execute(
        select(func.count())
        .select_from(LanguageContentItem)
        .where(
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.skill == skill,
            LanguageContentItem.content_type == content_type,
            LanguageContentItem.level.in_(allowed_levels),
            LanguageContentItem.is_published.is_(True),
        )
    )
    lessons_total = int(total_q.scalar() or 0)

    avg_expr = func.avg(score_column) if score_column is not None else None
    if avg_expr is not None:
        completed_q = await db.execute(
            select(func.count(), avg_expr)
            .select_from(progress_model)
            .join(LanguageContentItem, LanguageContentItem.id == progress_model.content_item_id)
            .where(
                progress_model.student_id == student_id,
                LanguageContentItem.language_id == language_id,
                LanguageContentItem.skill == skill,
                LanguageContentItem.content_type == content_type,
                LanguageContentItem.level.in_(allowed_levels),
                LanguageContentItem.is_published.is_(True),
                completed_filter,
            )
        )
    else:
        completed_q = await db.execute(
            select(func.count())
            .select_from(progress_model)
            .join(LanguageContentItem, LanguageContentItem.id == progress_model.content_item_id)
            .where(
                progress_model.student_id == student_id,
                LanguageContentItem.language_id == language_id,
                LanguageContentItem.skill == skill,
                LanguageContentItem.content_type == content_type,
                LanguageContentItem.level.in_(allowed_levels),
                LanguageContentItem.is_published.is_(True),
                completed_filter,
            )
        )
    row = completed_q.one()
    lessons_completed = int(row[0] or 0)
    avg_score = float(row[1]) if avg_expr is not None and row[1] is not None else None
    growth = compute_growth_percent(
        lessons_completed=lessons_completed,
        lessons_total=lessons_total,
        average_score=avg_score,
    )
    return {
        "level": level.value,
        "content_level": level.value,
        "growth_percent": growth,
        "lessons_completed": lessons_completed,
        "lessons_total": lessons_total,
        "average_score_percent": round(avg_score, 1) if avg_score is not None else None,
    }


async def _vocabulary_growth(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    level: LanguageLevel | None,
) -> dict:
    empty = {
        "level": level.value if level else None,
        "content_level": None,
        "known_words": 0,
        "learning_words": 0,
        "total_words": 0,
        "growth_percent": 0,
    }
    if not level:
        return empty

    content_level = await resolve_content_level(
        db,
        language_id=language_id,
        content_type="vocabulary",
        student_level=level,
        skill=None,
    )
    if not content_level:
        return empty

    total_q = await db.execute(
        select(func.count())
        .select_from(LanguageContentItem)
        .where(
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.content_type == "vocabulary",
            LanguageContentItem.level == content_level,
            LanguageContentItem.is_published.is_(True),
        )
    )
    total_words = int(total_q.scalar() or 0)

    lemmas_q = await db.execute(
        select(LanguageContentItem.body_json).where(
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.content_type == "vocabulary",
            LanguageContentItem.level == content_level,
            LanguageContentItem.is_published.is_(True),
        )
    )
    lemmas = [
        normalize_word((row[0] or {}).get("word") or "")
        for row in lemmas_q.all()
        if normalize_word((row[0] or {}).get("word") or "")
    ]
    known = learning = 0
    if lemmas:
        prog_q = await db.execute(
            select(LanguageVocabularyProgress.status, func.count())
            .where(
                LanguageVocabularyProgress.student_id == student_id,
                LanguageVocabularyProgress.language_id == language_id,
                LanguageVocabularyProgress.lemma.in_(lemmas),
            )
            .group_by(LanguageVocabularyProgress.status)
        )
        for status, cnt in prog_q.all():
            if status == LanguageVocabularyStatus.known:
                known = int(cnt)
            elif status == LanguageVocabularyStatus.learning:
                learning = int(cnt)

    growth = int(round(100 * known / total_words)) if total_words else 0
    return {
        "level": level.value,
        "content_level": content_level.value,
        "known_words": known,
        "learning_words": learning,
        "total_words": total_words,
        "growth_percent": min(100, growth),
    }


async def build_skill_growth_snapshot(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    analytics: LanguageAnalytics | None,
) -> dict:
    reading = await _skill_growth_for_level(
        db,
        student_id=student_id,
        language_id=language_id,
        skill=LanguageSkill.reading,
        level=analytics.reading_level if analytics else None,
        progress_model=LanguageReadingProgress,
        content_type="lesson",
        completed_filter=LanguageReadingProgress.status == LanguageContentProgressStatus.completed,
        score_column=LanguageReadingProgress.score_percent,
    )
    listening = await _skill_growth_for_level(
        db,
        student_id=student_id,
        language_id=language_id,
        skill=LanguageSkill.listening,
        level=analytics.listening_level if analytics else None,
        progress_model=LanguageListeningProgress,
        content_type="lesson",
        completed_filter=LanguageListeningProgress.status == LanguageContentProgressStatus.completed,
        score_column=LanguageListeningProgress.score_percent,
    )
    writing = await _skill_growth_for_level(
        db,
        student_id=student_id,
        language_id=language_id,
        skill=LanguageSkill.writing,
        level=analytics.writing_level if analytics else None,
        progress_model=LanguageWritingProgress,
        content_type="writing_prompt",
        completed_filter=LanguageWritingProgress.completed_at.isnot(None),
        score_column=LanguageWritingProgress.score_percent,
    )
    speaking = await _skill_growth_for_level(
        db,
        student_id=student_id,
        language_id=language_id,
        skill=LanguageSkill.speaking,
        level=analytics.speaking_level if analytics else None,
        progress_model=LanguageSpeakingProgress,
        content_type="speaking_prompt",
        completed_filter=LanguageSpeakingProgress.completed_at.isnot(None),
    )
    vocabulary = await _vocabulary_growth(
        db,
        student_id=student_id,
        language_id=language_id,
        level=analytics.reading_level if analytics else None,
    )

    # Completion is measured against a fixed target, not the (effectively infinite, AI-generated)
    # total pool — otherwise reading/listening would sit at ~0% forever.
    def _completion(skill_growth: dict) -> int:
        total = skill_growth["lessons_total"]
        if total <= 0:
            return 0
        denom = min(total, GROWTH_TARGET_LESSONS)
        return int(min(100, round(100 * skill_growth["lessons_completed"] / denom)))

    reading_completion = _completion(reading)
    listening_completion = _completion(listening)
    writing_completion = _completion(writing)
    speaking_completion = _completion(speaking)

    completed_activities = (
        reading["lessons_completed"]
        + listening["lessons_completed"]
        + writing["lessons_completed"]
        + speaking["lessons_completed"]
    )
    return {
        "reading": reading,
        "listening": listening,
        "writing": writing,
        "speaking": speaking,
        "vocabulary": vocabulary,
        "reading_completion_percent": reading_completion,
        "listening_completion_percent": listening_completion,
        "writing_completion_percent": writing_completion,
        "speaking_completion_percent": speaking_completion,
        "completed_activities": completed_activities,
        "vocabulary_learned": vocabulary["known_words"],
        "vocabulary_learning": vocabulary["learning_words"],
        "writing_completed": writing["lessons_completed"],
        "speaking_completed": speaking["lessons_completed"],
    }


async def refresh_language_analytics(db: AsyncSession, *, student_id: int, language_id: int | None = None) -> LanguageAnalytics:
    language = await get_default_language(db) if language_id is None else None
    lang_id = language_id or language.id
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": lang_id})
    if not analytics:
        analytics = LanguageAnalytics(student_id=student_id, language_id=lang_id)
        db.add(analytics)
        await db.flush()

    growth = await build_skill_growth_snapshot(db, student_id=student_id, language_id=lang_id, analytics=analytics)
    analytics.skill_growth_json = growth

    # Progress toward the next CEFR level, derived from completed lessons at each skill's
    # current level (averaged across the four skills).
    # POLICY: lesson completion NEVER auto-promotes a CEFR level. reading_level / listening_level
    # / writing_level / speaking_level are changed ONLY by explicit reassessment (the placement /
    # level-up test). Here we only surface readiness — we do not touch the per-skill levels below.
    skill_progress = [int(growth.get(s, {}).get("growth_percent") or 0) for s in ("reading", "listening", "writing", "speaking")]
    analytics.target_progress_percent = int(round(sum(skill_progress) / len(skill_progress))) if skill_progress else 0

    known_q = await db.execute(
        select(func.count())
        .select_from(LanguageVocabularyProgress)
        .where(
            LanguageVocabularyProgress.student_id == student_id,
            LanguageVocabularyProgress.language_id == lang_id,
            LanguageVocabularyProgress.status == LanguageVocabularyStatus.known,
        )
    )
    analytics.vocabulary_count = int(known_q.scalar() or 0)

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
    return analytics


async def get_streak(db: AsyncSession, *, student_id: int, language_id: int) -> LanguageStreak | None:
    result = await db.execute(
        select(LanguageStreak).where(
            LanguageStreak.student_id == student_id,
            LanguageStreak.language_id == language_id,
        )
    )
    return result.scalar_one_or_none()
