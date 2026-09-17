"""Learning Journey graph contracts — read-only projection for UI."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_learning_journey.enums import JourneyLevelStatus, JourneyStageStatus

LEARNING_JOURNEY_SCHEMA_VERSION = 1
LEARNING_JOURNEY_PACKAGE = "language_learning_journey"


@dataclass(frozen=True, slots=True)
class JourneyStage:
    grammar_id: str
    display_code: str
    display_name: str
    stage_index: int
    status: JourneyStageStatus
    mastery_state: str
    overall_mastery: float
    estimated_minutes: int
    skills: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class JourneyLevel:
    cefr: str
    status: JourneyLevelStatus
    expanded: bool
    completed_count: int
    total_count: int
    stages: tuple[JourneyStage, ...]


@dataclass(frozen=True, slots=True)
class JourneyProgress:
    cefr_label: str
    stage_index: int
    stage_total_in_level: int
    level_percent: float
    overall_completed: int
    overall_total: int


@dataclass(frozen=True, slots=True)
class JourneyGraph:
    enabled: bool
    anchor_cefr: str
    current_grammar_id: str | None
    next_grammar_id: str | None
    curriculum_version: str
    progress: JourneyProgress
    levels: tuple[JourneyLevel, ...]
    schema_version: int = LEARNING_JOURNEY_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "anchor_cefr": self.anchor_cefr,
            "current_grammar_id": self.current_grammar_id,
            "next_grammar_id": self.next_grammar_id,
            "curriculum_version": self.curriculum_version,
            "progress": {
                "cefr_label": self.progress.cefr_label,
                "stage_index": self.progress.stage_index,
                "stage_total_in_level": self.progress.stage_total_in_level,
                "level_percent": self.progress.level_percent,
                "overall_completed": self.progress.overall_completed,
                "overall_total": self.progress.overall_total,
            },
            "levels": [
                {
                    "cefr": lv.cefr,
                    "status": lv.status.value,
                    "expanded": lv.expanded,
                    "completed_count": lv.completed_count,
                    "total_count": lv.total_count,
                    "stages": [
                        {
                            "grammar_id": s.grammar_id,
                            "display_code": s.display_code,
                            "display_name": s.display_name,
                            "stage_index": s.stage_index,
                            "status": s.status.value,
                            "mastery_state": s.mastery_state,
                            "overall_mastery": s.overall_mastery,
                            "estimated_minutes": s.estimated_minutes,
                            "skills": list(s.skills),
                        }
                        for s in lv.stages
                    ],
                }
                for lv in self.levels
            ],
            "schema_version": self.schema_version,
        }
