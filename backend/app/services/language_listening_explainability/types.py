"""Types for the Learning Path & Explainability Engine (Phase 3.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.language_listening_explainability.facts import ExplainabilityFacts


class ObjectivePathStatus(StrEnum):
    not_started = "Not Started"
    learning = "Learning"
    practicing = "Practicing"
    review = "Review"
    mastered = "Mastered"


@dataclass(frozen=True, slots=True)
class LessonExplainability:
    why_this_lesson: str
    why_this_topic: str
    why_this_format: str
    why_this_difficulty: str
    why_these_questions: str
    current_focus: str
    current_goal: str
    challenge_reason: str
    confidence_reason: str
    review_reason: str
    next_recommendation: str
    teacher_note: str
    student_tip: str

    def to_dict(self) -> dict[str, str]:
        return {
            "why_this_lesson": self.why_this_lesson,
            "why_this_topic": self.why_this_topic,
            "why_this_format": self.why_this_format,
            "why_this_difficulty": self.why_this_difficulty,
            "why_these_questions": self.why_these_questions,
            "current_focus": self.current_focus,
            "current_goal": self.current_goal,
            "challenge_reason": self.challenge_reason,
            "confidence_reason": self.confidence_reason,
            "review_reason": self.review_reason,
            "next_recommendation": self.next_recommendation,
            "teacher_note": self.teacher_note,
            "student_tip": self.student_tip,
        }


@dataclass(frozen=True, slots=True)
class LearningPathObjective:
    objective_id: str
    label: str
    confidence: float
    coverage: float
    mastery: float
    status: str
    next_recommendation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "objective_id": self.objective_id,
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "coverage": round(self.coverage, 4),
            "mastery": round(self.mastery, 4),
            "status": self.status,
            "next_recommendation": self.next_recommendation,
        }


@dataclass(frozen=True, slots=True)
class LearningPath:
    level: str
    journey_title: str
    objectives: tuple[LearningPathObjective, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "journey_title": self.journey_title,
            "objectives": [o.to_dict() for o in self.objectives],
        }


@dataclass(frozen=True, slots=True)
class TeacherSummary:
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    recent_improvement: str
    current_bottleneck: str
    recommended_next_challenge: str
    review_priorities: tuple[str, ...]
    suggested_transcript_styles: tuple[str, ...]
    suggested_situations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "recent_improvement": self.recent_improvement,
            "current_bottleneck": self.current_bottleneck,
            "recommended_next_challenge": self.recommended_next_challenge,
            "review_priorities": list(self.review_priorities),
            "suggested_transcript_styles": list(self.suggested_transcript_styles),
            "suggested_situations": list(self.suggested_situations),
        }


@dataclass(frozen=True, slots=True)
class StudentSummary:
    what_improved: str
    what_needs_practice: str
    why_today_matters: str
    how_helps_future: str
    study_tip: str
    motivational_sentence: str

    def to_dict(self) -> dict[str, str]:
        return {
            "what_improved": self.what_improved,
            "what_needs_practice": self.what_needs_practice,
            "why_today_matters": self.why_today_matters,
            "how_helps_future": self.how_helps_future,
            "study_tip": self.study_tip,
            "motivational_sentence": self.motivational_sentence,
        }


@dataclass(frozen=True, slots=True)
class ExplainabilityTelemetry:
    generation_time_ms: float
    signals_used: tuple[str, ...]
    missing_signals: tuple[str, ...]
    coverage_completeness: float

    def to_dict(self) -> dict[str, object]:
        return {
            "generation_time_ms": round(self.generation_time_ms, 3),
            "signals_used": list(self.signals_used),
            "missing_signals": list(self.missing_signals),
            "coverage_completeness": round(self.coverage_completeness, 4),
        }


@dataclass(frozen=True, slots=True)
class ExplainabilityResult:
    lesson: LessonExplainability
    learning_path: LearningPath
    teacher_summary: TeacherSummary
    student_summary: StudentSummary
    telemetry: ExplainabilityTelemetry
    cefr_level: str
    facts: ExplainabilityFacts | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "cefr_level": self.cefr_level,
            "lesson": self.lesson.to_dict(),
            "learning_path": self.learning_path.to_dict(),
            "teacher_summary": self.teacher_summary.to_dict(),
            "student_summary": self.student_summary.to_dict(),
            "telemetry": self.telemetry.to_dict(),
        }
        if self.facts is not None:
            payload["facts"] = self.facts.to_dict()
        return payload


@dataclass
class ExplainabilitySignals:
    """Read-only snapshot extracted from lesson metadata and learner state."""

    intelligence: dict[str, object] = field(default_factory=dict)
    curriculum: dict[str, object] = field(default_factory=dict)
    goal: dict[str, object] = field(default_factory=dict)
    confidence_lesson: dict[str, object] = field(default_factory=dict)
    challenge_lesson: dict[str, object] = field(default_factory=dict)
    question_types: tuple[str, ...] = ()
    cefr_level: str = ""
    weak_skills: tuple[str, ...] = ()

    @property
    def present_keys(self) -> list[str]:
        keys: list[str] = []
        if self.intelligence:
            keys.append("listening_intelligence")
        if self.curriculum:
            keys.append("listening_curriculum")
        if self.goal:
            keys.append("listening_learning_goal")
        if self.confidence_lesson:
            keys.append("listening_confidence_lesson")
        if self.challenge_lesson:
            keys.append("listening_challenge_lesson")
        if self.question_types:
            keys.append("question_types")
        if self.cefr_level:
            keys.append("cefr_level")
        if self.weak_skills:
            keys.append("weak_skills")
        return keys
