"""Types for the Listening Intelligence Engine (Phase 2.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.services.language_listening_quality.types import (
    ListeningQualitySpec,
    ListeningSituationKind,
    NarrativeArc,
    OpeningStyle,
    PaceHint,
    TranscriptFormatHint,
)


class ListeningCategory(StrEnum):
    travel = "travel"
    daily_life = "daily_life"
    health = "health"
    education = "education"
    business = "business"
    technology = "technology"
    public_services = "public_services"
    entertainment = "entertainment"
    culture = "culture"
    environment = "environment"
    news = "news"
    customer_service = "customer_service"


class DifficultyBand(StrEnum):
    easy = "easy"
    normal = "normal"
    challenging = "challenging"


class NarrativeFormat(StrEnum):
    """Human-facing narrative format labels for rotation tracking."""

    dialogue = "dialogue"
    interview = "interview"
    lecture = "lecture"
    news = "news"
    announcement = "announcement"
    podcast = "podcast"
    story = "story"
    panel = "panel"
    monologue = "monologue"
    discussion = "discussion"


@dataclass(frozen=True, slots=True)
class ListeningHistoryEntry:
    situation: str
    category: str
    format_hint: str
    narrative_format: str
    difficulty_band: str
    narrative_arc: str
    level: str


@dataclass(frozen=True, slots=True)
class ListeningIntelligencePlan:
    """Weighted selection output for the next listening generation."""

    level: str
    situation: ListeningSituationKind
    category: ListeningCategory
    format_hint: TranscriptFormatHint
    narrative_format: NarrativeFormat
    difficulty_band: DifficultyBand
    narrative_arc: NarrativeArc
    opening_style: OpeningStyle
    ending_style: str
    pace: PaceHint
    speaker_count: int
    quality_spec: ListeningQualitySpec
    selection_score: float
    selection_reason: str

    def to_metadata(self) -> dict[str, str | float]:
        return {
            "level": self.level,
            "situation": self.situation.value,
            "category": self.category.value,
            "format_hint": self.format_hint.value,
            "narrative_format": self.narrative_format.value,
            "difficulty_band": self.difficulty_band.value,
            "narrative_arc": self.narrative_arc.value,
            "opening_style": self.opening_style.value,
            "pace": self.pace.value,
            "selection_score": round(self.selection_score, 4),
            "selection_reason": self.selection_reason,
        }

    def to_history_entry(self) -> ListeningHistoryEntry:
        return ListeningHistoryEntry(
            situation=self.situation.value,
            category=self.category.value,
            format_hint=self.format_hint.value,
            narrative_format=self.narrative_format.value,
            difficulty_band=self.difficulty_band.value,
            narrative_arc=self.narrative_arc.value,
            level=self.level,
        )


@dataclass
class ListeningDiversityStats:
    total_generations: int = 0
    situation_counts: dict[str, int] = field(default_factory=dict)
    category_counts: dict[str, int] = field(default_factory=dict)
    format_counts: dict[str, int] = field(default_factory=dict)
    difficulty_counts: dict[str, int] = field(default_factory=dict)
    max_consecutive_same_situation: int = 0
    cooldown_violations: int = 0
    diversity_score: float = 0.0
    most_used_situations: list[tuple[str, int]] = field(default_factory=list)
    least_used_situations: list[tuple[str, int]] = field(default_factory=list)
    average_repetitions: float = 0.0
