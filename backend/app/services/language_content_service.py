"""Published language lessons from language_content_items."""

from __future__ import annotations

import copy

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progress import LanguageListeningProgress, LanguageReadingProgress
from app.models.language.tts_cache import LanguageLessonAudioCache
from app.models.media import MediaObject
from app.services.language_subscription_service import get_default_language

DEFAULT_PASS_PERCENT = 70

LEVEL_ORDER = [
    LanguageLevel.A1,
    LanguageLevel.A2,
    LanguageLevel.B1,
    LanguageLevel.B2,
    LanguageLevel.C1,
    LanguageLevel.C2,
]


def _level_rank(level: LanguageLevel) -> int:
    try:
        return LEVEL_ORDER.index(level)
    except ValueError:
        return 0


async def _published_levels_for_content_type(
    db: AsyncSession,
    *,
    language_id: int,
    content_type: str,
    skill: LanguageSkill | None = None,
) -> list[LanguageLevel]:
    q = select(LanguageContentItem.level).where(
        LanguageContentItem.language_id == language_id,
        LanguageContentItem.content_type == content_type,
        LanguageContentItem.is_published.is_(True),
    )
    if skill is not None:
        q = q.where(LanguageContentItem.skill == skill)
    result = await db.execute(q.group_by(LanguageContentItem.level))
    levels = [row[0] for row in result.all() if row[0] is not None]
    return sorted(levels, key=_level_rank)


async def _resolve_content_level(
    db: AsyncSession,
    *,
    language_id: int,
    content_type: str,
    student_level: LanguageLevel,
    skill: LanguageSkill | None = None,
) -> LanguageLevel | None:
    available = await _published_levels_for_content_type(
        db, language_id=language_id, content_type=content_type, skill=skill
    )
    if not available:
        return None
    student_rank = _level_rank(student_level)
    if student_level in available:
        return student_level
    at_or_below = [lv for lv in available if _level_rank(lv) <= student_rank]
    if at_or_below:
        return at_or_below[-1]
    return available[0]


async def list_content_items(
    db: AsyncSession,
    *,
    student_id: int,
    content_type: str,
    skill: LanguageSkill | None,
    level_skill: LanguageSkill,
) -> tuple[LanguageLevel, LanguageLevel | None, list[LanguageContentItem]]:
    language = await get_default_language(db)
    student_level = await _student_skill_level(
        db, student_id=student_id, language_id=language.id, skill=level_skill
    )
    level = await _resolve_content_level(
        db,
        language_id=language.id,
        content_type=content_type,
        student_level=student_level,
        skill=skill,
    )
    if not level:
        return student_level, None, []
    q = select(LanguageContentItem).where(
        LanguageContentItem.language_id == language.id,
        LanguageContentItem.content_type == content_type,
        LanguageContentItem.level == level,
        LanguageContentItem.is_published.is_(True),
    )
    if skill is not None:
        q = q.where(LanguageContentItem.skill == skill)
    result = await db.execute(q.order_by(LanguageContentItem.sort_order, LanguageContentItem.id))
    return student_level, level, list(result.scalars().all())


async def get_content_item(
    db: AsyncSession,
    *,
    student_id: int,
    content_id: int,
    content_type: str,
    skill: LanguageSkill | None,
    level_skill: LanguageSkill,
) -> LanguageContentItem | None:
    language = await get_default_language(db)
    item = await db.get(LanguageContentItem, content_id)
    if not item or item.language_id != language.id or not item.is_published:
        return None
    if item.content_type != content_type:
        return None
    if skill is not None and item.skill != skill:
        return None
    owner_id = getattr(item, "student_id", None)
    if owner_id is not None and int(owner_id) != int(student_id):
        return None
    # NOTE: no level gate here. Adaptive reading serves cross-level content by id, so a direct
    # fetch/submit must work for any valid published item the student was given.
    return item


def normalize_word(word: str) -> str:
    return (word or "").strip().lower()[:120]


async def _published_levels_for_skill(
    db: AsyncSession,
    *,
    language_id: int,
    skill: LanguageSkill,
) -> list[LanguageLevel]:
    result = await db.execute(
        select(LanguageContentItem.level)
        .where(
            LanguageContentItem.language_id == language_id,
            LanguageContentItem.skill == skill,
            LanguageContentItem.content_type == "lesson",
            LanguageContentItem.is_published.is_(True),
        )
        .group_by(LanguageContentItem.level)
    )
    levels = [row[0] for row in result.all() if row[0] is not None]
    return sorted(levels, key=_level_rank)


async def _resolve_lesson_level(
    db: AsyncSession,
    *,
    language_id: int,
    skill: LanguageSkill,
    student_level: LanguageLevel,
) -> LanguageLevel | None:
    """Pick published content level: exact match, else highest available <= student level."""
    available = await _published_levels_for_skill(db, language_id=language_id, skill=skill)
    if not available:
        return None
    student_rank = _level_rank(student_level)
    if student_level in available:
        return student_level
    at_or_below = [lv for lv in available if _level_rank(lv) <= student_rank]
    if at_or_below:
        return at_or_below[-1]
    return available[0]


def _strip_answers(body: dict | None) -> dict:
    if not body:
        return {}
    out = copy.deepcopy(body)
    for q in out.get("questions") or []:
        # Never leak the answer or its rationale before the student submits.
        q.pop("correct_index", None)
        q.pop("explanation", None)
        q.pop("evidence_quote", None)
    # English-only platform: never expose legacy Arabic translation fields to the student.
    for key in [k for k in out if k.endswith("_ar")]:
        out.pop(key, None)
    return out


def _pass_threshold(body: dict | None) -> int:
    if not body:
        return DEFAULT_PASS_PERCENT
    try:
        return int(body.get("pass_threshold_percent") or DEFAULT_PASS_PERCENT)
    except (TypeError, ValueError):
        return DEFAULT_PASS_PERCENT


async def _student_skill_level(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill: LanguageSkill,
) -> LanguageLevel:
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics:
        lv = {
            LanguageSkill.reading: analytics.reading_level,
            LanguageSkill.listening: analytics.listening_level,
            LanguageSkill.writing: analytics.writing_level,
            LanguageSkill.speaking: analytics.speaking_level,
        }.get(skill)
        if lv:
            return lv
    return LanguageLevel.A1


async def list_lessons(
    db: AsyncSession,
    *,
    student_id: int,
    skill: LanguageSkill,
) -> tuple[LanguageLevel, LanguageLevel | None, list[LanguageContentItem], dict[int, object]]:
    language = await get_default_language(db)
    student_level = await _student_skill_level(db, student_id=student_id, language_id=language.id, skill=skill)
    level = await _resolve_lesson_level(
        db, language_id=language.id, skill=skill, student_level=student_level
    )
    if not level:
        return student_level, None, [], {}
    result = await db.execute(
        select(LanguageContentItem)
        .where(
            LanguageContentItem.language_id == language.id,
            LanguageContentItem.skill == skill,
            LanguageContentItem.content_type == "lesson",
            LanguageContentItem.level == level,
            LanguageContentItem.is_published.is_(True),
        )
        .order_by(LanguageContentItem.sort_order, LanguageContentItem.id)
    )
    items = list(result.scalars().all())
    progress_map: dict[int, object] = {}
    if not items:
        return student_level, level, items, progress_map
    ids = [i.id for i in items]
    if skill == LanguageSkill.reading:
        prog = await db.execute(
            select(LanguageReadingProgress).where(
                LanguageReadingProgress.student_id == student_id,
                LanguageReadingProgress.content_item_id.in_(ids),
            )
        )
        progress_map = {p.content_item_id: p for p in prog.scalars().all()}
    else:
        prog = await db.execute(
            select(LanguageListeningProgress).where(
                LanguageListeningProgress.student_id == student_id,
                LanguageListeningProgress.content_item_id.in_(ids),
            )
        )
        progress_map = {p.content_item_id: p for p in prog.scalars().all()}
    return student_level, level, items, progress_map


async def get_reading_lesson(
    db: AsyncSession,
    *,
    student_id: int,
    content_id: int,
) -> tuple[LanguageContentItem, object | None]:
    language = await get_default_language(db)
    item = await db.get(LanguageContentItem, content_id)
    # No level gate: adaptive reading serves cross-level passages by id, so fetch/submit must
    # work for any valid published reading item the student was given.
    if (
        not item
        or item.language_id != language.id
        or item.skill != LanguageSkill.reading
        or item.content_type != "lesson"
        or not item.is_published
    ):
        return None, None  # type: ignore[return-value]
    owner_id = getattr(item, "student_id", None)
    if owner_id is not None and int(owner_id) != int(student_id):
        return None, None  # type: ignore[return-value]
    prog = await db.execute(
        select(LanguageReadingProgress).where(
            LanguageReadingProgress.student_id == student_id,
            LanguageReadingProgress.content_item_id == content_id,
        )
    )
    return item, prog.scalar_one_or_none()


async def get_listening_lesson(
    db: AsyncSession,
    *,
    student_id: int,
    content_id: int,
) -> tuple[LanguageContentItem, object | None, str | None, bool]:
    language = await get_default_language(db)
    item = await db.get(LanguageContentItem, content_id)
    # No level gate: adaptive listening serves cross-level clips by id, so fetch/submit must accept
    # any published listening lesson in this language (mirrors get_reading_lesson).
    if (
        not item
        or item.language_id != language.id
        or item.skill != LanguageSkill.listening
        or item.content_type != "lesson"
        or not item.is_published
    ):
        return None, None, None, False  # type: ignore[return-value]
    owner_id = getattr(item, "student_id", None)
    if owner_id is not None and int(owner_id) != int(student_id):
        return None, None, None, False  # type: ignore[return-value]
    prog = await db.execute(
        select(LanguageListeningProgress).where(
            LanguageListeningProgress.student_id == student_id,
            LanguageListeningProgress.content_item_id == content_id,
        )
    )
    progress = prog.scalar_one_or_none()
    audio_url, audio_available = await resolve_listening_audio(db, item)
    return item, progress, audio_url, audio_available


async def resolve_listening_audio(db: AsyncSession, item: LanguageContentItem) -> tuple[str | None, bool]:
    if item.media_object_id:
        media = await db.get(MediaObject, item.media_object_id)
        if media and media.public_url:
            return media.public_url, True
    body = item.body_json or {}
    url = body.get("audio_url")
    if isinstance(url, str) and url.strip():
        return url.strip(), True
    cached = (
        await db.execute(
            select(LanguageLessonAudioCache.public_url)
            .where(
                LanguageLessonAudioCache.content_item_id == item.id,
                LanguageLessonAudioCache.voice_source.in_(("supertonic", "openai")),
                LanguageLessonAudioCache.public_url.is_not(None),
            )
            .order_by(LanguageLessonAudioCache.generated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if isinstance(cached, str) and cached.strip():
        return cached.strip(), True
    return None, False


def lesson_body_for_student(item: LanguageContentItem) -> dict:
    return _strip_answers(item.body_json or {})


def get_answer_key(body: dict | None) -> dict[str, int]:
    keys: dict[str, int] = {}
    for q in (body or {}).get("questions") or []:
        qid = q.get("id")
        if qid is None:
            continue
        try:
            keys[str(qid)] = int(q.get("correct_index"))
        except (TypeError, ValueError):
            continue
    return keys


def pass_threshold_for_item(item: LanguageContentItem) -> int:
    return _pass_threshold(item.body_json)


# Public alias for analytics / progress rollups (content level fallback).
resolve_content_level = _resolve_content_level
