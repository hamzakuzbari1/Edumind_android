"""Types for language_speaking_lesson_experience (S10 student lesson bundle).

Assembles the S10 educational mission structure into a student-safe lesson bundle.
Exposes only learner-facing content (titles, instructions, teaching blocks, objective
text). Never exposes internal scoring, gating, mastery, evidence intent, or skill IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

LANGUAGE_SPEAKING_LESSON_EXPERIENCE_VERSION = "10.0.0"


@dataclass(frozen=True, slots=True)
class SpeakingLessonExperienceMissionItem:
    """One student-facing mission card in the lesson bundle."""

    mission_id: str
    kind: str
    execution_mode: str
    order_index: int
    title: str
    learner_instructions: str
    is_live: bool
    is_executable: bool = False
    objectives: tuple[str, ...] = ()
    teaching_blocks: tuple[dict[str, object], ...] = ()
    tasks: tuple[dict[str, object], ...] = ()

    def to_student_dict(self) -> dict[str, object]:
        return {
            "mission_id": self.mission_id,
            "kind": self.kind,
            "execution_mode": self.execution_mode,
            "order_index": self.order_index,
            "title": self.title,
            "learner_instructions": self.learner_instructions,
            "is_live": self.is_live,
            "is_executable": self.is_executable,
            "objectives": list(self.objectives),
            "teaching_blocks": [dict(b) for b in self.teaching_blocks],
            "tasks": [dict(t) for t in self.tasks],
        }


@dataclass(frozen=True, slots=True)
class SpeakingLessonExperienceBundle:
    """Student-safe speaking lesson bundle projected from a blueprint (S10)."""

    version: str = LANGUAGE_SPEAKING_LESSON_EXPERIENCE_VERSION
    blueprint_id: str = ""
    session_goal: str = ""
    current_focus_label: str = ""
    missions: tuple[SpeakingLessonExperienceMissionItem, ...] = field(default_factory=tuple)

    def to_student_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "blueprint_id": self.blueprint_id,
            "session_goal": self.session_goal,
            "current_focus_label": self.current_focus_label,
            "missions": [m.to_student_dict() for m in self.missions],
        }
