"""Build lesson context for confidence updates from stored metadata."""

from __future__ import annotations

from app.services.language_listening_confidence.types import LessonConfidenceContext
from app.services.language_listening_curriculum.memory import CURRICULUM_KEY
from app.services.language_listening_intelligence.memory import HISTORY_KEY


def _question_objectives(body: dict) -> tuple[str, ...]:
    objectives: list[str] = []
    for q in body.get("questions") or []:
        if not isinstance(q, dict):
            continue
        qtype = str(q.get("type") or "detail").strip()
        if qtype and qtype not in objectives:
            objectives.append(qtype)
    return tuple(objectives)


def _legacy_lesson_context(
    body: dict,
    *,
    lesson_index: int,
    level: str | None,
) -> LessonConfidenceContext | None:
    """Fallback when listening_intelligence.situation is absent (seed / legacy lessons)."""
    questions = body.get("questions") or []
    if not questions:
        return None

    intel = body.get(HISTORY_KEY) if isinstance(body.get(HISTORY_KEY), dict) else {}
    curriculum = body.get(CURRICULUM_KEY) if isinstance(body.get(CURRICULUM_KEY), dict) else {}

    situation = (
        str(intel.get("situation") or body.get("situation") or body.get("topic") or "").strip()
        or "legacy_listening"
    )
    narrative_format = str(
        intel.get("narrative_format") or body.get("narrative_format") or body.get("format") or "dialogue"
    )
    format_hint = str(intel.get("format_hint") or body.get("format_hint") or "")
    difficulty_band = str(
        intel.get("difficulty_band")
        or body.get("difficulty_band")
        or body.get("difficulty")
        or "normal"
    )
    category = str(intel.get("category") or body.get("topic") or body.get("category") or "daily_life")
    pace = str(intel.get("pace") or body.get("pace") or "conversational")

    curriculum_objectives = tuple(str(o) for o in (curriculum.get("objectives") or []) if o)
    question_objectives = _question_objectives(body)
    lesson_objectives = curriculum_objectives or question_objectives

    skills = tuple(str(s) for s in (curriculum.get("skill_focus") or []) if s)
    if not skills and question_objectives:
        skills = question_objectives

    speaker_count = int(
        curriculum.get("speaker_count")
        or intel.get("speaker_count")
        or body.get("speaker_count")
        or 1
    )

    if level and not intel.get("level"):
        category = category or str(level).lower()

    return LessonConfidenceContext(
        situation=situation,
        narrative_format=narrative_format,
        format_hint=format_hint,
        difficulty_band=difficulty_band,
        speaker_count=speaker_count,
        lesson_objectives=lesson_objectives,
        skill_focus=skills,
        lesson_index=lesson_index,
        category=category,
        pace=pace,
    )


def lesson_context_from_body(
    body: dict,
    *,
    lesson_index: int,
    level: str | None = None,
) -> LessonConfidenceContext | None:
    intel = body.get(HISTORY_KEY) if isinstance(body.get(HISTORY_KEY), dict) else {}
    curriculum = body.get(CURRICULUM_KEY) if isinstance(body.get(CURRICULUM_KEY), dict) else {}
    if intel.get("situation"):
        skills = tuple(str(s) for s in (curriculum.get("skill_focus") or []) if s)
        objectives = tuple(str(o) for o in (curriculum.get("objectives") or []) if o)
        return LessonConfidenceContext(
            situation=str(intel.get("situation") or ""),
            narrative_format=str(intel.get("narrative_format") or ""),
            format_hint=str(intel.get("format_hint") or ""),
            difficulty_band=str(intel.get("difficulty_band") or "normal"),
            speaker_count=int(curriculum.get("speaker_count") or intel.get("speaker_count") or 1),
            lesson_objectives=objectives,
            skill_focus=skills,
            lesson_index=lesson_index,
            category=str(intel.get("category") or ""),
            pace=str(intel.get("pace") or "conversational"),
        )
    return _legacy_lesson_context(body, lesson_index=lesson_index, level=level)
