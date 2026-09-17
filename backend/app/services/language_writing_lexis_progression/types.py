"""Types for Writing Lexis Progression (W0)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_writing.enums import LexisCategory, LexisState, WritingGoal, WritingTopicId


@dataclass(frozen=True, slots=True)
class WritingLexisState:
    """Per-student lemma mastery within a vocabulary category."""

    student_id: int
    language_id: int
    lemma: str
    category: LexisCategory
    state: LexisState
    topic_id: WritingTopicId | None = None
    evidence_count: int = 0
    last_seen_at: str | None = None
    introduced_at: str | None = None


@dataclass(frozen=True, slots=True)
class LexisCategoryBalance:
    """Target mix of vocabulary categories for a lesson."""

    category: LexisCategory
    target_weight: float
    min_lemmas: int = 0
    max_new_lemmas: int = 3


@dataclass(frozen=True, slots=True)
class LexisBalancePlan:
    """Balanced lexis plan for selection/generation."""

    goal: WritingGoal
    topic_id: WritingTopicId
    category_targets: tuple[LexisCategoryBalance, ...]
    reuse_mastered_lemmas: tuple[str, ...] = ()
    reinforce_lemmas: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LexisProgressionSnapshot:
    """Read-only snapshot for selection and coach."""

    states: tuple[WritingLexisState, ...]
    mastered_count_by_category: dict[str, int] = field(default_factory=dict)
