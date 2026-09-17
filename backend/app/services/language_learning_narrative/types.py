"""Narrative output types (Phase 2.1)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class LessonNarrative:
    """Student-facing lesson-scoped copy — produced only by Learning Narrative Builder."""

    reason_selected: str
    why_this_lesson: str
    student_focus: tuple[str, ...]
    expected_improvement: tuple[str, ...]
    reward: str
    coach_summary: str
    challenge_reason: str
    next_after_this: str
    situation_label: str
    level_note: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "reason_selected": self.reason_selected,
            "why_this_lesson": self.why_this_lesson,
            "student_focus": list(self.student_focus),
            "expected_improvement": list(self.expected_improvement),
            "reward": self.reward,
            "coach_summary": self.coach_summary,
            "challenge_reason": self.challenge_reason,
            "next_after_this": self.next_after_this,
            "situation_label": self.situation_label,
            "level_note": self.level_note,
        }


@dataclass(frozen=True, slots=True)
class AfterLessonNarrative:
    headline: str
    summary: str
    improved: tuple[str, ...]
    needs_practice: tuple[str, ...]
    next_lesson_teaser: str
    coach_summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "headline": self.headline,
            "summary": self.summary,
            "improved": list(self.improved),
            "needs_practice": list(self.needs_practice),
            "next_lesson_teaser": self.next_lesson_teaser,
            "coach_summary": self.coach_summary,
        }


@dataclass(frozen=True, slots=True)
class TimelineStepNarrative:
    key: str
    label: str
    done: bool = False
    active: bool = False
    current: bool = False


@dataclass(frozen=True, slots=True)
class HistoryEventNarrative:
    period: str
    text: str


@dataclass(frozen=True, slots=True)
class JourneyNarrative:
    """Student-facing journey-scoped copy — Journey Builder only (Phase 2.3)."""

    journey_headline: str
    current_step_label: str
    promotion_progress_message: str
    unlock_checklist: tuple[str, ...]
    timeline_steps: tuple[TimelineStepNarrative, ...]
    history_events: tuple[HistoryEventNarrative, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "journey_headline": self.journey_headline,
            "current_step_label": self.current_step_label,
            "promotion_progress_message": self.promotion_progress_message,
            "unlock_checklist": list(self.unlock_checklist),
            "timeline_steps": [
                {
                    "key": s.key,
                    "label": s.label,
                    "done": s.done,
                    "active": s.active,
                    "current": s.current,
                }
                for s in self.timeline_steps
            ],
            "history_events": [{"period": e.period, "text": e.text} for e in self.history_events],
        }


# Fields that constitute student-facing educational copy owned by this package.
STUDENT_NARRATIVE_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "reason_selected",
        "why_this_lesson",
        "student_focus",
        "expected_improvement",
        "reward",
        "coach_summary",
        "challenge_reason",
        "next_after_this",
        "situation_label",
        "level_note",
        "headline",
        "summary",
        "improved",
        "needs_practice",
        "next_lesson_teaser",
    }
)
