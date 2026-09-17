from typing import Literal

from pydantic import BaseModel, Field

TeacherTeachingStyle = Literal[
    "step_by_step",
    "concept_first",
    "exam_focused",
    "practical_examples",
    "discussion_based",
]
TeacherTone = Literal["friendly", "strict", "balanced"]
TeacherQuestionStyle = Literal["asks_questions", "explains_only", "mixed"]
TeacherMotivationLevel = Literal["low", "medium", "high"]


class TeacherAiProfileOut(BaseModel):
    teacher_teaching_style: TeacherTeachingStyle = "step_by_step"
    teacher_tone: TeacherTone = "balanced"
    teacher_question_style: TeacherQuestionStyle = "mixed"
    teacher_motivation_level: TeacherMotivationLevel = "medium"
    teacher_display_name: str | None = None
    teacher_bio: str | None = None
    teacher_signature_phrase: str | None = None


class TeacherAiProfileUpdate(BaseModel):
    teacher_teaching_style: TeacherTeachingStyle
    teacher_tone: TeacherTone
    teacher_question_style: TeacherQuestionStyle
    teacher_motivation_level: TeacherMotivationLevel
    teacher_display_name: str | None = Field(default=None, max_length=255)
    teacher_bio: str | None = Field(default=None, max_length=2000)
    teacher_signature_phrase: str | None = Field(default=None, max_length=500)
