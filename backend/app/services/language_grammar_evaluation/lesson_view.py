"""Extract minimal LessonPackageView from ActivitySpecification payload (V1.8)."""

from __future__ import annotations

import json
from typing import Any

from app.services.language_grammar_activity_spec import ActivitySpecification
from app.services.language_grammar_evaluation.types import LessonPackageView


def _parse_str_list(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, (list, tuple)):
        return tuple(str(x).strip() for x in raw if str(x).strip())
    text = str(raw).strip()
    if not text:
        return ()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        if "\n" in text:
            return tuple(p.strip() for p in text.splitlines() if p.strip())
        return (text,)
    if isinstance(parsed, list):
        return tuple(str(x).strip() for x in parsed if str(x).strip())
    return ()


def lesson_view_from_payload(payload: dict[str, str] | None) -> LessonPackageView:
    data = dict(payload or {})
    return LessonPackageView(
        expected_patterns=_parse_str_list(data.get("expected_patterns")),
        grammar_focus=str(data.get("grammar_focus") or ""),
        teacher_opening=str(data.get("teacher_opening") or ""),
        main_activity=str(data.get("main_activity") or ""),
        extras={
            k: str(v)
            for k, v in data.items()
            if k
            not in {
                "expected_patterns",
                "grammar_focus",
                "teacher_opening",
                "main_activity",
            }
        },
    )


def lesson_view_from_specification(specification: ActivitySpecification) -> LessonPackageView:
    return lesson_view_from_payload(dict(specification.payload))


def merge_expected_patterns(
    *,
    explicit: tuple[str, ...] | None,
    lesson: LessonPackageView,
) -> tuple[str, ...]:
    if explicit:
        return tuple(p for p in explicit if str(p).strip())
    return tuple(lesson.expected_patterns)
