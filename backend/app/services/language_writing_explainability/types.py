"""Types for Writing Facts Layer (W0/W2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing.enums import (
    ContextComplexity,
    OfficialWritingCEFR,
    WritingArc,
    WritingGoal,
    WritingLessonLifecycle,
)
from app.services.language_writing_evaluator.types import WritingEvaluationResult


@dataclass(frozen=True, slots=True)
class ContextComplexityFacts:
    """Internal facts for context complexity (student copy translated in narrative)."""

    level: ContextComplexity
    label_internal: str
    student_label: str
    selection_reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "level": int(self.level),
            "label_internal": self.label_internal,
            "student_label": self.student_label,
            "selection_reason": self.selection_reason,
        }


@dataclass(frozen=True, slots=True)
class WritingLessonFacts:
    """Canonical facts bundle for one writing lesson — internal only."""

    official_cefr: OfficialWritingCEFR
    lesson_cefr: OfficialWritingCEFR
    arc_stage: WritingArc
    goal: WritingGoal
    topic_id: str
    chain_id: str
    chain_node_id: str
    context_complexity: ContextComplexityFacts
    lifecycle: WritingLessonLifecycle
    weak_skills: tuple[str, ...] = ()
    grammar_focus: str = ""
    lexis_categories: tuple[str, ...] = ()
    mission_why: str = ""
    mission_goal: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "official_cefr": self.official_cefr.value,
            "lesson_cefr": self.lesson_cefr.value,
            "arc_stage": self.arc_stage.value,
            "goal": self.goal.value,
            "topic_id": self.topic_id,
            "chain_id": self.chain_id,
            "chain_node_id": self.chain_node_id,
            "context_complexity": self.context_complexity.to_dict(),
            "lifecycle": self.lifecycle.value,
            "weak_skills": list(self.weak_skills),
            "grammar_focus": self.grammar_focus,
            "lexis_categories": list(self.lexis_categories),
            "mission_why": self.mission_why,
            "mission_goal": self.mission_goal,
        }


@dataclass(frozen=True, slots=True)
class TrendFacts:
    """Longitudinal coach layer facts — owned by explainability (facts output shape)."""

    trend_headline: str
    improvement_areas: tuple[str, ...]
    sustained_skills: tuple[str, ...]
    regression_warnings: tuple[str, ...]
    comparison_window_lessons: int
    comparison_window_days: int
    generated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "trend_headline": self.trend_headline,
            "improvement_areas": list(self.improvement_areas),
            "sustained_skills": list(self.sustained_skills),
            "regression_warnings": list(self.regression_warnings),
            "comparison_window_lessons": self.comparison_window_lessons,
            "comparison_window_days": self.comparison_window_days,
            "generated_at": self.generated_at,
        }


@dataclass(frozen=True, slots=True)
class WritingProgressionFacts:
    """Internal progression snapshot for journey (not student-facing raw scores)."""

    learning_stage: int
    learning_stage_label: str
    promotion_eligible: bool
    weak_skills: tuple[str, ...] = ()
    next_milestone: str = ""


@dataclass(frozen=True, slots=True)
class WritingFactsBundle:
    """Complete writing facts for narrative and bundle builders."""

    lesson: WritingLessonFacts
    progression: WritingProgressionFacts | None = None
    trend: TrendFacts | None = None
    evaluation: WritingEvaluationResult | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"lesson": self.lesson.to_dict()}
        if self.progression is not None:
            payload["progression"] = {
                "learning_stage": self.progression.learning_stage,
                "learning_stage_label": self.progression.learning_stage_label,
                "promotion_eligible": self.progression.promotion_eligible,
                "weak_skills": list(self.progression.weak_skills),
                "next_milestone": self.progression.next_milestone,
            }
        if self.trend is not None:
            payload["trend"] = self.trend.to_dict()
        if self.evaluation is not None:
            payload["evaluation"] = self.evaluation.to_facts_dict()
        return payload
