"""Types for Writing Portfolio (W0)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing_coach.types import WritingFeedback


@dataclass(frozen=True, slots=True)
class WritingPortfolioEntry:
    """Append-only snapshot when a lesson completes — educational archive only."""

    entry_id: str
    student_id: int
    language_id: int
    content_item_id: int
    mission_title: str
    mission_why: str
    first_draft_text: str
    final_draft_text: str
    coach_feedback: WritingFeedback
    completion_date: str
    skills_learned: tuple[str, ...] = ()
    progress_highlights: tuple[str, ...] = ()
    topic_id: str = ""
    chain_node_id: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "entry_id": self.entry_id,
            "mission_title": self.mission_title,
            "mission_why": self.mission_why,
            "first_draft_text": self.first_draft_text,
            "final_draft_text": self.final_draft_text,
            "coach_feedback": self.coach_feedback.to_student_dict(),
            "completion_date": self.completion_date,
            "skills_learned": list(self.skills_learned),
            "progress_highlights": list(self.progress_highlights),
            "topic_id": self.topic_id,
            "chain_node_id": self.chain_node_id,
        }


@dataclass(frozen=True, slots=True)
class WritingPortfolioIndex:
    """Lightweight portfolio listing."""

    entries: tuple[WritingPortfolioEntry, ...] = ()
    total_completed: int = 0
