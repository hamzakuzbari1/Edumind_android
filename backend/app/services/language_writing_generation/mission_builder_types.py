"""Mission Builder types (W4) — student-facing mission assembled from blueprint only."""

from __future__ import annotations

from dataclasses import dataclass

MISSION_BUILDER_VERSION = "4.0.0"


@dataclass(frozen=True, slots=True)
class WritingEstimatedTime:
    """Time display for student mission."""

    writing_minutes: int
    revision_minutes: int
    total_minutes: int


@dataclass(frozen=True, slots=True)
class WritingStudentMission:
    """Student-facing mission — assembled from blueprint; no educational decisions."""

    mission_title: str
    mission_context: str
    instructions: tuple[str, ...]
    constraints: tuple[str, ...]
    success_criteria: tuple[str, ...]
    estimated_time: WritingEstimatedTime
    learning_outcomes: tuple[str, ...]
    tips: tuple[str, ...]
    checklist: tuple[str, ...]
    expected_output: str
    writing_prompt: str
    blueprint_id: str
    blueprint_version: str
    blueprint_hash: str
    builder_version: str = MISSION_BUILDER_VERSION

    def to_student_dict(self) -> dict[str, object]:
        return {
            "mission_title": self.mission_title,
            "mission_context": self.mission_context,
            "instructions": list(self.instructions),
            "constraints": list(self.constraints),
            "success_criteria": list(self.success_criteria),
            "estimated_time": {
                "writing_minutes": self.estimated_time.writing_minutes,
                "revision_minutes": self.estimated_time.revision_minutes,
                "total_minutes": self.estimated_time.total_minutes,
            },
            "learning_outcomes": list(self.learning_outcomes),
            "tips": list(self.tips),
            "checklist": list(self.checklist),
            "expected_output": self.expected_output,
            "writing_prompt": self.writing_prompt,
            "blueprint_id": self.blueprint_id,
            "blueprint_version": self.blueprint_version,
            "blueprint_hash": self.blueprint_hash,
        }


def mission_fields_complete(mission: WritingStudentMission) -> bool:
    return bool(
        mission.mission_title.strip()
        and mission.mission_context.strip()
        and mission.instructions
        and mission.constraints
        and mission.success_criteria
        and mission.estimated_time.total_minutes > 0
        and mission.learning_outcomes
        and mission.checklist
        and mission.expected_output
        and mission.writing_prompt.strip()
    )
