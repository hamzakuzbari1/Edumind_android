"""Learning Curriculum Engine — educational progression for listening (Phase 2.3)."""

from app.services.language_listening_curriculum.engine import (
    build_curriculum_prompt_block,
    compute_curriculum_telemetry,
    recommend_curriculum_plan,
)
from app.services.language_listening_curriculum.history import load_curriculum_history
from app.services.language_listening_curriculum.memory import CURRICULUM_KEY
from app.services.language_listening_curriculum.types import (
    CurriculumHistoryEntry,
    CurriculumRecommendation,
    CurriculumTelemetry,
)

__all__ = (
    "CURRICULUM_KEY",
    "CurriculumHistoryEntry",
    "CurriculumRecommendation",
    "CurriculumTelemetry",
    "build_curriculum_prompt_block",
    "compute_curriculum_telemetry",
    "load_curriculum_history",
    "recommend_curriculum_plan",
)
