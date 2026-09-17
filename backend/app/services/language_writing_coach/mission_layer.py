"""Coach Mission layer (W2.1 frozen) — lesson opening contract after narrative builder."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing_curriculum.types import WritingGoalProfile


COACH_MISSION_LAYER_VERSION = "2.1.0"

# Pipeline position (frozen):
#   Evaluator → Facts → Learning Narrative Builder → **Coach Mission Layer** → Lesson Experience
#
# The mission layer does NOT generate lesson prompts or AI content.
# It assembles student-facing mission framing from facts + narrative + goal profile + node metadata.


@dataclass(frozen=True, slots=True)
class WritingCoachMission:
    """Student-facing lesson opening — produced after narrative builder.

    Required fields (W2.1):
    - todays_mission
    - todays_focus
    - todays_goal
    - success_criteria
    - expected_learning_outcomes
    """

    todays_mission: str
    todays_focus: str
    todays_goal: str
    success_criteria: tuple[str, ...]
    expected_learning_outcomes: tuple[str, ...]
    goal_label: str = ""
    mission_style: str = ""
    architecture_version: str = COACH_MISSION_LAYER_VERSION

    def to_student_dict(self) -> dict[str, object]:
        return {
            "todays_mission": self.todays_mission,
            "todays_focus": self.todays_focus,
            "todays_goal": self.todays_goal,
            "success_criteria": list(self.success_criteria),
            "expected_learning_outcomes": list(self.expected_learning_outcomes),
            "goal_label": self.goal_label,
            "mission_style": self.mission_style,
        }


@dataclass(frozen=True, slots=True)
class CoachMissionInput:
    """Inputs for mission assembly — no LLM in W2."""

    goal_profile: WritingGoalProfile
    narrative_why: str
    narrative_focus: str
    narrative_goal: str
    node_learning_outcomes: tuple[str, ...]
    node_label: str
    task_type: str
    genre: str
    success_criteria_from_node: tuple[str, ...] = ()


def mission_fields_complete(mission: WritingCoachMission) -> bool:
    return bool(
        mission.todays_mission.strip()
        and mission.todays_focus.strip()
        and mission.todays_goal.strip()
        and mission.success_criteria
        and mission.expected_learning_outcomes
    )
