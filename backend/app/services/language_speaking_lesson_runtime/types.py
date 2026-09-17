"""E2 lesson runtime types — cursor only; educational content comes from frozen package."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

LESSON_RUNTIME_SCHEMA_VERSION = "2.0.0"


class LessonRuntimeSection(StrEnum):
    not_started = "not_started"
    introduction = "introduction"
    reading = "reading"
    vocabulary = "vocabulary"
    teaching = "teaching"
    mini_practice = "mini_practice"
    completed = "completed"


SECTION_ORDER: tuple[LessonRuntimeSection, ...] = (
    LessonRuntimeSection.not_started,
    LessonRuntimeSection.introduction,
    LessonRuntimeSection.reading,
    LessonRuntimeSection.vocabulary,
    LessonRuntimeSection.teaching,
    LessonRuntimeSection.mini_practice,
    LessonRuntimeSection.completed,
)


def next_section(current: LessonRuntimeSection) -> LessonRuntimeSection | None:
    try:
        idx = SECTION_ORDER.index(current)
    except ValueError:
        return LessonRuntimeSection.introduction
    if idx >= len(SECTION_ORDER) - 1:
        return None
    return SECTION_ORDER[idx + 1]


@dataclass(slots=True)
class LessonRuntimeState:
    """Persisted runtime memory — never stores regenerated educational content."""

    package_id: str
    content_item_id: int | None
    constraints_fingerprint: str
    content_fingerprint: str
    current_section: LessonRuntimeSection
    completed_sections: list[str] = field(default_factory=list)
    viewed_vocabulary_ids: list[str] = field(default_factory=list)
    completed_teaching_block_ids: list[str] = field(default_factory=list)
    mini_practice_prep_done: bool = False
    ready_for_discussion: bool = False
    position_hint: str = ""
    started_at: str = ""
    updated_at: str = ""
    schema_version: str = LESSON_RUNTIME_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "package_id": self.package_id,
            "content_item_id": self.content_item_id,
            "constraints_fingerprint": self.constraints_fingerprint,
            "content_fingerprint": self.content_fingerprint,
            "current_section": self.current_section.value,
            "completed_sections": list(self.completed_sections),
            "viewed_vocabulary_ids": list(self.viewed_vocabulary_ids),
            "completed_teaching_block_ids": list(self.completed_teaching_block_ids),
            "mini_practice_prep_done": self.mini_practice_prep_done,
            "ready_for_discussion": self.ready_for_discussion,
            "position_hint": self.position_hint,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> LessonRuntimeState | None:
        if not isinstance(raw, dict) or not raw.get("package_id"):
            return None
        section_raw = str(raw.get("current_section") or "not_started")
        try:
            section = LessonRuntimeSection(section_raw)
        except ValueError:
            section = LessonRuntimeSection.not_started
        return LessonRuntimeState(
            package_id=str(raw.get("package_id") or ""),
            content_item_id=int(raw["content_item_id"])
            if raw.get("content_item_id") is not None
            else None,
            constraints_fingerprint=str(raw.get("constraints_fingerprint") or ""),
            content_fingerprint=str(raw.get("content_fingerprint") or ""),
            current_section=section,
            completed_sections=[str(x) for x in (raw.get("completed_sections") or [])],
            viewed_vocabulary_ids=[str(x) for x in (raw.get("viewed_vocabulary_ids") or [])],
            completed_teaching_block_ids=[
                str(x) for x in (raw.get("completed_teaching_block_ids") or [])
            ],
            mini_practice_prep_done=bool(raw.get("mini_practice_prep_done")),
            ready_for_discussion=bool(raw.get("ready_for_discussion")),
            position_hint=str(raw.get("position_hint") or ""),
            started_at=str(raw.get("started_at") or ""),
            updated_at=str(raw.get("updated_at") or ""),
            schema_version=str(raw.get("schema_version") or LESSON_RUNTIME_SCHEMA_VERSION),
        )


# Alias for package exports
types_version = LESSON_RUNTIME_SCHEMA_VERSION
