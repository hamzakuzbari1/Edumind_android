"""Official progression storage and read layer (Phase 4.2.1–4.2.3).

Phase 4.2.3 switches educational selectors to Official CEFR when
LANG_PROGRESSION_OFFICIAL_SELECT is true (default false).

Feature flags (all default false):
  LANG_PROGRESSION_ENABLED       — enables progression writes (dual-write)
  LANG_PROGRESSION_DUAL_READ     — legacy alias; use OFFICIAL_SELECT for 4.2.3
  LANG_PROGRESSION_OFFICIAL_SELECT — educational selection reads Official CEFR

Promotion lifecycle flag matrix (listening):
  ENABLED=false — ensure_progression_row() does not create rows; promotion APIs
    return a structured denial (never HTTP 500). Selectors use analytics when
    OFFICIAL_SELECT=false, else progression-first with analytics fallback.
  ENABLED=true, OFFICIAL_SELECT=false — progression row created from analytics;
    promotion APIs work; selectors still read analytics per-skill levels.
  ENABLED=true, OFFICIAL_SELECT=true — full promotion lifecycle; selectors read
    official_listening_cefr from progression.

Official listening CEFR write policy:
  - Placement: initialization only (dual-write into progression + analytics).
  - Lesson submit: never promotes official_listening_cefr.
  - Promotion test: never promotes official_listening_cefr.
  - Official Promotion engine: the ONLY runtime writer of official_listening_cefr.
  After Official Promotion, analytics.listening_level is synchronized to match
  (see sync_analytics_listening_level).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.language.analytics import LanguageAnalytics
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.progression import LanguageProgression, LanguageProgressionEvent
from app.services.language_level_utils import CEFR_RANK, bottleneck_level, primary_focus_and_strength

OfficialCefrSource = Literal["progression", "analytics"]

_SKILL_TO_PROGRESSION_ATTR = {
    "reading": "official_reading_cefr",
    "listening": "official_listening_cefr",
    "writing": "official_writing_cefr",
    "speaking": "official_speaking_cefr",
}

_SKILL_TO_ANALYTICS_ATTR = {
    "reading": "reading_level",
    "listening": "listening_level",
    "writing": "writing_level",
    "speaking": "speaking_level",
}


@dataclass(frozen=True)
class OfficialCefrRead:
    """Result of reading Official CEFR for one skill or overall."""

    level: LanguageLevel
    source: OfficialCefrSource
    skill: str  # "reading" | "listening" | "writing" | "speaking" | "overall"


def progression_enabled() -> bool:
    """Master write flag — default false."""
    return bool(get_settings().LANG_PROGRESSION_ENABLED)


def dual_read_enabled() -> bool:
    """Legacy selector flag — prefer official_select_enabled() for Phase 4.2.3+."""
    return bool(get_settings().LANG_PROGRESSION_DUAL_READ)


def official_select_enabled() -> bool:
    """When true, educational selectors read Official CEFR (progression-first)."""
    return bool(get_settings().LANG_PROGRESSION_OFFICIAL_SELECT)


PROGRESSION_UNAVAILABLE_REASON = (
    "Listening progression is not available. "
    "LANG_PROGRESSION_ENABLED must be true and language analytics must exist."
)


def _analytics_skill_level(
    analytics: LanguageAnalytics | None,
    skill: LanguageSkill,
    *,
    default: LanguageLevel,
) -> LanguageLevel:
    if analytics is None:
        return default
    attr = _SKILL_TO_ANALYTICS_ATTR[skill.value]
    level = getattr(analytics, attr)
    return level or default


def _analytics_overall_level(
    analytics: LanguageAnalytics | None,
    *,
    default: LanguageLevel = LanguageLevel.A1,
) -> LanguageLevel:
    if analytics is None:
        return default
    level_map = {
        key: getattr(analytics, attr).value if getattr(analytics, attr) else None
        for key, attr in _SKILL_TO_ANALYTICS_ATTR.items()
    }
    return analytics.overall_level_internal or bottleneck_level(level_map) or default


def _analytics_level_if_higher(
    analytics: LanguageAnalytics | None,
    skill_key: str,
    current: LanguageLevel,
) -> LanguageLevel | None:
    """Return analytics level only when it safely corrects a stale lower progression row."""
    if analytics is None:
        return None
    attr = _SKILL_TO_ANALYTICS_ATTR[skill_key]
    analytics_level = getattr(analytics, attr)
    if analytics_level is None:
        return None
    if CEFR_RANK.get(analytics_level, 0) > CEFR_RANK.get(current, 0):
        return analytics_level
    return None


def _analytics_overall_if_higher(
    analytics: LanguageAnalytics | None,
    current: LanguageLevel,
) -> LanguageLevel | None:
    """Return analytics overall only when it safely corrects a stale lower progression row."""
    analytics_level = _analytics_overall_level(analytics, default=current)
    if CEFR_RANK.get(analytics_level, 0) > CEFR_RANK.get(current, 0):
        return analytics_level
    return None


def _coerce_language_level(value: LanguageLevel | str | None, default: LanguageLevel) -> LanguageLevel:
    if isinstance(value, LanguageLevel):
        return value
    try:
        return LanguageLevel(str(value))
    except (TypeError, ValueError):
        return default


def _reconcile_stale_lower_progression_from_analytics(
    row: LanguageProgression,
    analytics: LanguageAnalytics | None,
) -> bool:
    """Persist analytics levels only when they correct stale lower progression columns."""
    if analytics is None:
        return False

    changed = False
    official_levels: dict[str, LanguageLevel] = {}
    for skill_key, progression_attr in _SKILL_TO_PROGRESSION_ATTR.items():
        current = _coerce_language_level(getattr(row, progression_attr, None), LanguageLevel.A1)
        corrected = _analytics_level_if_higher(analytics, skill_key, current)
        if corrected is not None:
            setattr(row, progression_attr, corrected)
            current = corrected
            changed = True
        official_levels[skill_key] = current

    current_overall = _coerce_language_level(
        getattr(row, "official_overall_cefr", None),
        LanguageLevel.A1,
    )
    corrected_overall = _analytics_overall_if_higher(analytics, current_overall)
    bottleneck = bottleneck_level({key: level for key, level in official_levels.items()})
    candidates = [level for level in (corrected_overall, bottleneck) if level is not None]
    if candidates:
        best = max(candidates, key=lambda level: CEFR_RANK.get(level, 0))
        if CEFR_RANK.get(best, 0) > CEFR_RANK.get(current_overall, 0):
            row.official_overall_cefr = best
            changed = True

    if changed:
        row.version = int(row.version or 0) + 1
        row.updated_at = datetime.now(timezone.utc)
    return changed


async def select_skill_level(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill: LanguageSkill | str,
    default: LanguageLevel = LanguageLevel.A1,
) -> LanguageLevel:
    """Educational selector: Official CEFR when OFFICIAL_SELECT else analytics (legacy)."""
    if official_select_enabled():
        return (
            await get_official_cefr(
                db, student_id=student_id, language_id=language_id, skill=skill
            )
        ).level
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    skill_key = _normalize_skill(skill)
    return _analytics_skill_level(analytics, LanguageSkill(skill_key), default=default)


async def select_skill_level_str(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill: LanguageSkill | str,
    default: LanguageLevel = LanguageLevel.A2,
) -> str:
    return (await select_skill_level(
        db, student_id=student_id, language_id=language_id, skill=skill, default=default
    )).value


async def select_overall_level(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    default: LanguageLevel = LanguageLevel.A1,
) -> LanguageLevel:
    """Educational selector for overall / curriculum / difficulty base level."""
    if official_select_enabled():
        return (
            await get_official_overall_cefr(
                db, student_id=student_id, language_id=language_id
            )
        ).level
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    return _analytics_overall_level(analytics, default=default)


async def select_overall_level_str(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    default: LanguageLevel = LanguageLevel.A1,
) -> str:
    return (await select_overall_level(
        db, student_id=student_id, language_id=language_id, default=default
    )).value


async def select_all_skill_levels(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> dict[str, str | None]:
    """Per-skill + overall levels for hub/access/learner context."""
    if official_select_enabled():
        out: dict[str, str | None] = {}
        for skill_key in ("reading", "listening", "writing", "speaking"):
            read = await get_official_cefr(
                db, student_id=student_id, language_id=language_id, skill=skill_key
            )
            out[skill_key] = read.level.value
        overall = await get_official_overall_cefr(
            db, student_id=student_id, language_id=language_id
        )
        out["overall"] = overall.level.value
        return out

    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics is None:
        return {"reading": None, "listening": None, "writing": None, "speaking": None, "overall": None}
    levels = {
        key: getattr(analytics, attr).value if getattr(analytics, attr) else None
        for key, attr in _SKILL_TO_ANALYTICS_ATTR.items()
    }
    overall = _analytics_overall_level(analytics)
    levels["overall"] = overall.value if overall else None
    return levels


def _normalize_skill(skill: LanguageSkill | str) -> str:
    if isinstance(skill, LanguageSkill):
        return skill.value
    return str(skill).strip().lower()


def official_levels_from_analytics(analytics: LanguageAnalytics) -> dict[str, LanguageLevel]:
    """Backfill rule: all official skill columns = bottleneck(analytics skill levels).

    Used only for legacy backfill — not for placement/exam dual-write.
    """
    level_map = {
        "reading": analytics.reading_level.value if analytics.reading_level else None,
        "listening": analytics.listening_level.value if analytics.listening_level else None,
        "writing": analytics.writing_level.value if analytics.writing_level else None,
        "speaking": analytics.speaking_level.value if analytics.speaking_level else None,
    }
    overall = bottleneck_level(level_map) or LanguageLevel.A1
    return {
        "reading": overall,
        "listening": overall,
        "writing": overall,
        "speaking": overall,
        "overall": overall,
    }


def mirror_levels_from_analytics(analytics: LanguageAnalytics) -> dict[str, LanguageLevel]:
    """Exact mirror of analytics per-skill columns for dual-write after placement/exam/promotion."""
    level_map = {
        "reading": analytics.reading_level.value if analytics.reading_level else None,
        "listening": analytics.listening_level.value if analytics.listening_level else None,
        "writing": analytics.writing_level.value if analytics.writing_level else None,
        "speaking": analytics.speaking_level.value if analytics.speaking_level else None,
    }
    overall = (
        analytics.overall_level_internal
        or bottleneck_level(level_map)
        or LanguageLevel.A1
    )
    default = overall if isinstance(overall, LanguageLevel) else LanguageLevel.A1

    def _skill_level(key: str) -> LanguageLevel:
        raw = level_map.get(key)
        if raw is None:
            return default
        return LanguageLevel(raw)

    return {
        "reading": _skill_level("reading"),
        "listening": _skill_level("listening"),
        "writing": _skill_level("writing"),
        "speaking": _skill_level("speaking"),
        "overall": default,
    }


async def get_official_cefr(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill: LanguageSkill | str,
) -> OfficialCefrRead:
    """Centralized Official CEFR read — progression row first, analytics fallback.

    Future code (Phase 4.2.3+) must use this helper instead of reading analytics directly.
    """
    skill_key = _normalize_skill(skill)
    if skill_key not in _SKILL_TO_PROGRESSION_ATTR:
        raise ValueError(f"Unknown skill: {skill}")

    row = await db.get(LanguageProgression, {"student_id": student_id, "language_id": language_id})
    if row is not None:
        level = getattr(row, _SKILL_TO_PROGRESSION_ATTR[skill_key])
        analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
        corrected = _analytics_level_if_higher(analytics, skill_key, level)
        if corrected is not None:
            return OfficialCefrRead(level=corrected, source="analytics", skill=skill_key)
        return OfficialCefrRead(level=level, source="progression", skill=skill_key)

    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics is not None:
        level = getattr(analytics, _SKILL_TO_ANALYTICS_ATTR[skill_key]) or LanguageLevel.A1
        return OfficialCefrRead(level=level, source="analytics", skill=skill_key)

    return OfficialCefrRead(level=LanguageLevel.A1, source="analytics", skill=skill_key)


async def get_official_overall_cefr(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> OfficialCefrRead:
    """Official overall CEFR — progression first, analytics bottleneck fallback."""
    row = await db.get(LanguageProgression, {"student_id": student_id, "language_id": language_id})
    if row is not None:
        analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
        corrected = _analytics_overall_if_higher(analytics, row.official_overall_cefr)
        if corrected is not None:
            return OfficialCefrRead(level=corrected, source="analytics", skill="overall")
        return OfficialCefrRead(
            level=row.official_overall_cefr,
            source="progression",
            skill="overall",
        )

    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics is not None:
        levels = mirror_levels_from_analytics(analytics)
        return OfficialCefrRead(level=levels["overall"], source="analytics", skill="overall")

    return OfficialCefrRead(level=LanguageLevel.A1, source="analytics", skill="overall")


async def ensure_progression_row(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LanguageProgression | None:
    """Ensure a progression row exists, creating from analytics when missing.

    Writes only when LANG_PROGRESSION_ENABLED is true.
    """
    row = await db.get(LanguageProgression, {"student_id": student_id, "language_id": language_id})
    if row is not None:
        analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
        if _reconcile_stale_lower_progression_from_analytics(row, analytics):
            await record_progression_event(
                db,
                student_id=student_id,
                language_id=language_id,
                event_type="official_levels_reconciled_from_higher_analytics",
                payload_json={"source": "ensure_progression_row"},
                force=True,
            )
            await db.flush()
        return row

    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics is None:
        return None

    return await backfill_from_analytics_row(db, analytics, force=False)


async def record_progression_event(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    event_type: str,
    payload_json: dict[str, Any] | None = None,
    force: bool = False,
) -> LanguageProgressionEvent | None:
    """Append an audit event. Respects LANG_PROGRESSION_ENABLED unless force=True (backfill)."""
    if not force and not progression_enabled():
        return None
    event = LanguageProgressionEvent(
        student_id=student_id,
        language_id=language_id,
        event_type=event_type,
        payload_json=payload_json,
    )
    db.add(event)
    await db.flush()
    return event


async def upsert_official_levels(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    reading: LanguageLevel,
    listening: LanguageLevel,
    writing: LanguageLevel,
    speaking: LanguageLevel,
    overall: LanguageLevel | None = None,
    source: str,
    force: bool = False,
) -> LanguageProgression | None:
    """Create or update Official CEFR columns."""
    if not force and not progression_enabled():
        return None

    overall = overall or bottleneck_level(
        {
            "reading": reading.value,
            "listening": listening.value,
            "writing": writing.value,
            "speaking": speaking.value,
        }
    ) or reading

    row = await db.get(LanguageProgression, {"student_id": student_id, "language_id": language_id})
    is_new = row is None
    if row is None:
        row = LanguageProgression(student_id=student_id, language_id=language_id)
        db.add(row)

    row.official_reading_cefr = reading
    row.official_listening_cefr = listening
    row.official_writing_cefr = writing
    row.official_speaking_cefr = speaking
    row.official_overall_cefr = overall
    row.version = int(row.version or 0) + (0 if is_new else 1)
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()

    await record_progression_event(
        db,
        student_id=student_id,
        language_id=language_id,
        event_type="official_levels_upserted" if not is_new else "official_levels_created",
        payload_json={
            "source": source,
            "reading": reading.value,
            "listening": listening.value,
            "writing": writing.value,
            "speaking": speaking.value,
            "overall": overall.value,
        },
        force=force,
    )
    return row


async def sync_analytics_listening_level(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    listening_level: LanguageLevel,
) -> LanguageAnalytics | None:
    """Mirror official listening CEFR into analytics after Official Promotion (STAB-2).

    Updates only analytics.listening_level. Reading, writing, and speaking are
    untouched. Overall is recomputed with the existing bottleneck rule.
    """
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics is None:
        return None

    analytics.listening_level = listening_level
    levels = {
        "reading": analytics.reading_level.value if analytics.reading_level else None,
        "listening": analytics.listening_level.value,
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


async def sync_progression_from_skill_levels(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    skill_levels: dict[LanguageSkill, LanguageLevel],
    overall: LanguageLevel,
    source: str,
) -> LanguageProgression | None:
    """Dual-write: mirror exact per-skill levels from placement/exam/promotion."""
    return await upsert_official_levels(
        db,
        student_id=student_id,
        language_id=language_id,
        reading=skill_levels[LanguageSkill.reading],
        listening=skill_levels[LanguageSkill.listening],
        writing=skill_levels[LanguageSkill.writing],
        speaking=skill_levels[LanguageSkill.speaking],
        overall=overall,
        source=source,
    )


async def sync_progression_mirror_analytics(
    db: AsyncSession,
    analytics: LanguageAnalytics,
    *,
    source: str,
) -> LanguageProgression | None:
    """Dual-write: copy current analytics columns into progression (post-exam partial updates)."""
    levels = mirror_levels_from_analytics(analytics)
    return await upsert_official_levels(
        db,
        student_id=analytics.student_id,
        language_id=analytics.language_id,
        reading=levels["reading"],
        listening=levels["listening"],
        writing=levels["writing"],
        speaking=levels["speaking"],
        overall=levels["overall"],
        source=source,
    )


async def backfill_from_analytics_row(
    db: AsyncSession,
    analytics: LanguageAnalytics,
    *,
    force: bool = True,
) -> LanguageProgression | None:
    """Idempotent backfill for one analytics row (bottleneck rule)."""
    levels = official_levels_from_analytics(analytics)
    return await upsert_official_levels(
        db,
        student_id=analytics.student_id,
        language_id=analytics.language_id,
        reading=levels["reading"],
        listening=levels["listening"],
        writing=levels["writing"],
        speaking=levels["speaking"],
        overall=levels["overall"],
        source="backfill_analytics",
        force=force,
    )


async def count_progression_rows(db: AsyncSession) -> int:
    from sqlalchemy import func

    result = await db.execute(select(func.count()).select_from(LanguageProgression))
    return int(result.scalar() or 0)


async def count_analytics_rows(db: AsyncSession) -> int:
    from sqlalchemy import func

    result = await db.execute(select(func.count()).select_from(LanguageAnalytics))
    return int(result.scalar() or 0)
