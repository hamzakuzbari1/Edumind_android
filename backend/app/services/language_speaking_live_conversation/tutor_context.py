"""Minimal live tutor context for EVI session_settings (S7.5).

Never includes S2 knowledge model or curriculum progression data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LiveTutorContext:
    official_speaking_cefr: str
    speaking_goal: str
    activity_task: str
    teacher_persona: str
    conversation_objective: str
    allowed_behavior: str = "Supportive English tutor; encourage spoken practice; do not assess or promote CEFR."

    def to_session_settings(self) -> dict[str, object]:
        system_prompt = (
            f"You are {self.teacher_persona}. "
            f"Student official speaking CEFR (context only): {self.official_speaking_cefr}. "
            f"Goal: {self.speaking_goal}. "
            f"Activity: {self.activity_task}. "
            f"Objective: {self.conversation_objective}. "
            f"{self.allowed_behavior}"
        )
        return {
            "type": "session_settings",
            "system_prompt": system_prompt,
            "audio": {
                "encoding": "linear16",
                "channels": 1,
                "sample_rate": 16000,
            },
        }


def default_live_tutor_context(*, official_cefr: str = "B1", goal: str = "general_english") -> LiveTutorContext:
    return LiveTutorContext(
        official_speaking_cefr=official_cefr,
        speaking_goal=goal,
        activity_task="Have a short spoken conversation about daily life.",
        teacher_persona="a friendly English speaking tutor",
        conversation_objective="Help the student practice natural spoken English in a supportive dialogue.",
    )
