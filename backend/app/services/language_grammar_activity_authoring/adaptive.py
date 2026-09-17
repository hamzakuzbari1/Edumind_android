"""Adaptive Lesson Authoring context (V1.7).

Adaptive context influences HOW a lesson is taught.
Grammar Targets remain the ONLY authority for WHAT is taught.
Immutable snapshots only — no Runtime / mastery engine objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ADAPTIVE_SNAPSHOT_SCHEMA_VERSION = 1
ADAPTIVE_AUTHORING_PACKAGE_VERSION = "1.7.0"


@dataclass(frozen=True, slots=True)
class RecentErrorSummary:
    """Structured recent learner error — never raw conversation logs."""

    grammar_target: str
    pattern: str
    frequency: int = 1
    last_seen: str = ""
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class StudentLearningSnapshot:
    """Immutable student learning snapshot for adaptive authoring (HOW only)."""

    mastery_summary: str = ""
    recent_errors: tuple[RecentErrorSummary, ...] = ()
    recent_successes: tuple[str, ...] = ()
    commonly_missed_patterns: tuple[str, ...] = ()
    commonly_mastered_patterns: tuple[str, ...] = ()
    last_lesson_summary: str = ""
    last_activity_type: str = ""
    lesson_history_summary: str = ""
    confidence_summary: str = ""
    snapshot_version: int = ADAPTIVE_SNAPSHOT_SCHEMA_VERSION

    def is_empty(self) -> bool:
        return not (
            (self.mastery_summary or "").strip()
            or self.recent_errors
            or self.recent_successes
            or self.commonly_missed_patterns
            or self.commonly_mastered_patterns
            or (self.last_lesson_summary or "").strip()
            or (self.last_activity_type or "").strip()
            or (self.lesson_history_summary or "").strip()
            or (self.confidence_summary or "").strip()
        )

    def has_weakness_signal(self) -> bool:
        return bool(self.recent_errors or self.commonly_missed_patterns)

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "snapshot_version": self.snapshot_version,
            "mastery_summary": self.mastery_summary,
            "recent_errors": [
                {
                    "grammar_target": e.grammar_target,
                    "pattern": e.pattern,
                    "frequency": e.frequency,
                    "last_seen": e.last_seen,
                    "confidence": e.confidence,
                }
                for e in self.recent_errors
            ],
            "recent_successes": list(self.recent_successes),
            "commonly_missed_patterns": list(self.commonly_missed_patterns),
            "commonly_mastered_patterns": list(self.commonly_mastered_patterns),
            "last_lesson_summary": self.last_lesson_summary,
            "last_activity_type": self.last_activity_type,
            "lesson_history_summary": self.lesson_history_summary,
            "confidence_summary": self.confidence_summary,
        }

    def fingerprint_payload(self) -> dict[str, Any]:
        return self.to_prompt_dict()


@dataclass(frozen=True, slots=True)
class AdaptiveAuthoringContext:
    """HOW-to-teach surface — never selects or changes Grammar Targets."""

    learning_snapshot: StudentLearningSnapshot = field(default_factory=StudentLearningSnapshot)
    personalization_enabled: bool = True
    adaptive_version: str = ADAPTIVE_AUTHORING_PACKAGE_VERSION
    extras: dict[str, str] = field(default_factory=dict)

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "adaptive_version": self.adaptive_version,
            "personalization_enabled": self.personalization_enabled,
            "learning_snapshot": self.learning_snapshot.to_prompt_dict(),
            "extras": dict(self.extras),
        }


def empty_learning_snapshot() -> StudentLearningSnapshot:
    return StudentLearningSnapshot()


def learning_snapshot_from_mapping(raw: dict[str, Any] | None) -> StudentLearningSnapshot:
    data = dict(raw or {})
    errors_raw = data.get("recent_errors") or ()
    errors: list[RecentErrorSummary] = []
    for item in errors_raw:
        if not isinstance(item, dict):
            continue
        target = str(item.get("grammar_target") or "").strip()
        pattern = str(item.get("pattern") or "").strip()
        if not target or not pattern:
            continue
        conf = item.get("confidence")
        errors.append(
            RecentErrorSummary(
                grammar_target=target,
                pattern=pattern,
                frequency=int(item.get("frequency") or 1),
                last_seen=str(item.get("last_seen") or ""),
                confidence=float(conf) if conf is not None and conf != "" else None,
            )
        )
    return StudentLearningSnapshot(
        mastery_summary=str(data.get("mastery_summary") or ""),
        recent_errors=tuple(errors),
        recent_successes=tuple(str(x) for x in (data.get("recent_successes") or ()) if str(x).strip()),
        commonly_missed_patterns=tuple(
            str(x) for x in (data.get("commonly_missed_patterns") or ()) if str(x).strip()
        ),
        commonly_mastered_patterns=tuple(
            str(x) for x in (data.get("commonly_mastered_patterns") or ()) if str(x).strip()
        ),
        last_lesson_summary=str(data.get("last_lesson_summary") or ""),
        last_activity_type=str(data.get("last_activity_type") or ""),
        lesson_history_summary=str(data.get("lesson_history_summary") or ""),
        confidence_summary=str(data.get("confidence_summary") or ""),
        snapshot_version=int(data.get("snapshot_version") or ADAPTIVE_SNAPSHOT_SCHEMA_VERSION),
    )
