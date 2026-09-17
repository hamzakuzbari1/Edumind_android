"""Coach long-term memory architecture (W2.1 frozen) — design only, no storage."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MemorySignalKind(StrEnum):
    """Categories of longitudinal coach memory."""

    repeated_mistake = "repeated_mistake"
    repeated_strength = "repeated_strength"
    vocabulary_habit = "vocabulary_habit"
    grammar_habit = "grammar_habit"
    student_preference = "student_preference"
    grammar_trend = "grammar_trend"
    vocabulary_trend = "vocabulary_trend"
    writing_speed_trend = "writing_speed_trend"
    revision_behaviour = "revision_behaviour"
    topic_affinity = "topic_affinity"
    confidence_trend = "confidence_trend"
    learning_momentum = "learning_momentum"


class TrendDirection(StrEnum):
    """Direction of a longitudinal educational trend."""

    improving = "improving"
    stable = "stable"
    declining = "declining"
    insufficient_data = "insufficient_data"


@dataclass(frozen=True, slots=True)
class RepeatedPattern:
    """A mistake or strength seen across multiple lessons."""

    kind: MemorySignalKind
    code: str
    label: str
    occurrence_count: int
    last_seen_at: str
    lesson_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class VocabularyHabit:
    """Observed vocabulary tendency — fact for coach context, not a grade."""

    tendency: str
    evidence_lemmas: tuple[str, ...] = ()
    occurrence_count: int = 0


@dataclass(frozen=True, slots=True)
class GrammarHabit:
    """Observed grammar tendency."""

    structure: str
    tendency: str
    occurrence_count: int = 0


@dataclass(frozen=True, slots=True)
class GrammarTrend:
    """Longitudinal grammar performance signal."""

    structure: str
    direction: TrendDirection
    recent_accuracy: float
    lessons_in_window: int
    note_internal: str = ""


@dataclass(frozen=True, slots=True)
class VocabularyTrend:
    """Longitudinal vocabulary range and precision signal."""

    category: str
    direction: TrendDirection
    range_score: float
    precision_score: float
    note_internal: str = ""


@dataclass(frozen=True, slots=True)
class WritingSpeedTrend:
    """Drafting pace relative to goal time estimates."""

    direction: TrendDirection
    avg_words_per_minute: float
    avg_time_vs_estimate_ratio: float
    note_internal: str = ""


@dataclass(frozen=True, slots=True)
class RevisionBehaviour:
    """How the student revises across lessons."""

    avg_revision_turns: float
    responds_to_priority_fix: bool
    completes_without_coach_push: bool
    pattern_label: str  # e.g. "careful_reviser", "quick_submitter"


@dataclass(frozen=True, slots=True)
class TopicAffinity:
    """Favorite or avoided topics — selection hint only, not progression gate."""

    topic_id: str
    affinity: str  # favorite | avoided | neutral
    completion_count: int = 0
    avg_coach_approval_turns: float = 0.0


@dataclass(frozen=True, slots=True)
class ConfidenceTrend:
    """Coach-inferred confidence from revision patterns and self-reported prefs."""

    direction: TrendDirection
    signal_sources: tuple[str, ...] = ()
    note_internal: str = ""


@dataclass(frozen=True, slots=True)
class LearningMomentum:
    """Recent lesson completion and improvement velocity."""

    direction: TrendDirection
    lessons_completed_14d: int
    improvement_streak: int
    note_internal: str = ""


@dataclass(frozen=True, slots=True)
class StudentPreference:
    """Student-stated or inferred preferences — coach adapts tone only."""

    preference_key: str
    preference_value: str
    source: str = "inferred"  # inferred | stated


@dataclass(frozen=True, slots=True)
class CoachMemorySnapshot:
    """Read-only memory context for one coach turn — assembled by future storage layer.

    W2.1 FROZEN — future phases must extend signals, not replace this contract.

    Storage (future — NOT W2):
    - Table: `language_writing_coach_memory` (student_id, signal_kind, payload_json)
    - Updated after each coach-approved lesson completion
    - Portfolio may read summaries; progression must not depend on memory
    """

    student_id: int
    repeated_mistakes: tuple[RepeatedPattern, ...] = ()
    repeated_strengths: tuple[RepeatedPattern, ...] = ()
    vocabulary_habits: tuple[VocabularyHabit, ...] = ()
    grammar_habits: tuple[GrammarHabit, ...] = ()
    grammar_trends: tuple[GrammarTrend, ...] = ()
    vocabulary_trends: tuple[VocabularyTrend, ...] = ()
    writing_speed_trend: WritingSpeedTrend | None = None
    revision_behaviour: RevisionBehaviour | None = None
    favorite_topics: tuple[TopicAffinity, ...] = ()
    avoided_topics: tuple[TopicAffinity, ...] = ()
    confidence_trend: ConfidenceTrend | None = None
    learning_momentum: LearningMomentum | None = None
    preferences: tuple[StudentPreference, ...] = ()
    snapshot_version: str = "2.1.0"
    window_lessons: int = 10

    def to_coach_context_dict(self) -> dict[str, object]:
        """Internal coach context — not student API."""
        return {
            "repeated_mistakes": [{"code": p.code, "label": p.label, "count": p.occurrence_count} for p in self.repeated_mistakes],
            "repeated_strengths": [{"code": p.code, "label": p.label, "count": p.occurrence_count} for p in self.repeated_strengths],
            "vocabulary_habits": [{"tendency": v.tendency, "count": v.occurrence_count} for v in self.vocabulary_habits],
            "grammar_habits": [{"structure": g.structure, "tendency": g.tendency} for g in self.grammar_habits],
            "grammar_trends": [{"structure": t.structure, "direction": t.direction.value} for t in self.grammar_trends],
            "vocabulary_trends": [{"category": t.category, "direction": t.direction.value} for t in self.vocabulary_trends],
            "writing_speed_trend": (
                {"direction": self.writing_speed_trend.direction.value, "wpm": self.writing_speed_trend.avg_words_per_minute}
                if self.writing_speed_trend
                else None
            ),
            "revision_behaviour": (
                {"pattern": self.revision_behaviour.pattern_label, "avg_turns": self.revision_behaviour.avg_revision_turns}
                if self.revision_behaviour
                else None
            ),
            "favorite_topics": [t.topic_id for t in self.favorite_topics],
            "avoided_topics": [t.topic_id for t in self.avoided_topics],
            "confidence_trend": (
                {"direction": self.confidence_trend.direction.value} if self.confidence_trend else None
            ),
            "learning_momentum": (
                {"direction": self.learning_momentum.direction.value, "streak": self.learning_momentum.improvement_streak}
                if self.learning_momentum
                else None
            ),
            "preferences": [{"key": p.preference_key, "value": p.preference_value} for p in self.preferences],
            "window_lessons": self.window_lessons,
        }
