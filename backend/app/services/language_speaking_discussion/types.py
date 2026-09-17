"""E3 discussion runtime types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

DISCUSSION_RUNTIME_SCHEMA_VERSION = "3.0.0"
MAX_TURNS_STORED = 40
MAX_CORRECTIONS_STORED = 30


class DiscussionPhase(StrEnum):
    waiting_for_student = "waiting_for_student"
    student_answering = "student_answering"
    processing = "processing"
    assistant_reply = "assistant_reply"
    next_question = "next_question"
    completed = "completed"


@dataclass(slots=True)
class DiscussionTurn:
    role: str  # student | assistant | system
    text: str
    step_id: str
    correction_brief: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "text": self.text,
            "step_id": self.step_id,
            "correction_brief": self.correction_brief,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> DiscussionTurn:
        return DiscussionTurn(
            role=str(raw.get("role") or "assistant"),
            text=str(raw.get("text") or ""),
            step_id=str(raw.get("step_id") or ""),
            correction_brief=str(raw.get("correction_brief") or ""),
            created_at=str(raw.get("created_at") or ""),
        )


@dataclass(slots=True)
class DiscussionRuntimeState:
    package_id: str
    content_item_id: int | None
    content_fingerprint: str
    phase: DiscussionPhase
    step_index: int
    current_step_id: str
    assistant_turns_used: int = 0
    answered_step_ids: list[str] = field(default_factory=list)
    corrections_shown: list[dict[str, str]] = field(default_factory=list)
    turns: list[DiscussionTurn] = field(default_factory=list)
    completed: bool = False
    ready_for_alex: bool = False
    opening_shown: bool = False
    started_at: str = ""
    updated_at: str = ""
    schema_version: str = DISCUSSION_RUNTIME_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "package_id": self.package_id,
            "content_item_id": self.content_item_id,
            "content_fingerprint": self.content_fingerprint,
            "phase": self.phase.value,
            "step_index": self.step_index,
            "current_step_id": self.current_step_id,
            "assistant_turns_used": self.assistant_turns_used,
            "answered_step_ids": list(self.answered_step_ids),
            "corrections_shown": list(self.corrections_shown)[-MAX_CORRECTIONS_STORED:],
            "turns": [t.to_dict() for t in self.turns][-MAX_TURNS_STORED:],
            "completed": self.completed,
            "ready_for_alex": self.ready_for_alex,
            "opening_shown": self.opening_shown,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(raw: dict[str, Any] | None) -> DiscussionRuntimeState | None:
        if not isinstance(raw, dict) or not raw.get("package_id"):
            return None
        try:
            phase = DiscussionPhase(str(raw.get("phase") or "waiting_for_student"))
        except ValueError:
            phase = DiscussionPhase.waiting_for_student
        turns_raw = raw.get("turns") or []
        turns = [
            DiscussionTurn.from_dict(t) for t in turns_raw if isinstance(t, dict)
        ][-MAX_TURNS_STORED:]
        corrections = []
        for c in raw.get("corrections_shown") or []:
            if isinstance(c, dict):
                corrections.append({str(k): str(v) for k, v in c.items()})
        return DiscussionRuntimeState(
            package_id=str(raw.get("package_id") or ""),
            content_item_id=int(raw["content_item_id"])
            if raw.get("content_item_id") is not None
            else None,
            content_fingerprint=str(raw.get("content_fingerprint") or ""),
            phase=phase,
            step_index=max(0, int(raw.get("step_index") or 0)),
            current_step_id=str(raw.get("current_step_id") or ""),
            assistant_turns_used=max(0, int(raw.get("assistant_turns_used") or 0)),
            answered_step_ids=[str(x) for x in (raw.get("answered_step_ids") or [])],
            corrections_shown=corrections[-MAX_CORRECTIONS_STORED:],
            turns=turns,
            completed=bool(raw.get("completed")),
            ready_for_alex=bool(raw.get("ready_for_alex")),
            opening_shown=bool(raw.get("opening_shown")),
            started_at=str(raw.get("started_at") or ""),
            updated_at=str(raw.get("updated_at") or ""),
            schema_version=str(raw.get("schema_version") or DISCUSSION_RUNTIME_SCHEMA_VERSION),
        )
