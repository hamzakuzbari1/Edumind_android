"""Facts Layer (Phase 2.1) — structured, language-neutral lesson and journey signals."""

from app.services.language_learning_facts.assembler import assemble_lesson_facts
from app.services.language_learning_facts.labels import slug_label
from app.services.language_learning_facts.types import (
    ChallengeFacts,
    CurriculumFacts,
    GoalFacts,
    LessonFactsBundle,
    LevelContextFacts,
    ObjectiveConfidenceFact,
    ProgressionFacts,
    PromotionContextFacts,
    SelectionRationaleFacts,
    SituationFacts,
)

__all__ = (
    "ChallengeFacts",
    "CurriculumFacts",
    "GoalFacts",
    "LessonFactsBundle",
    "LevelContextFacts",
    "ObjectiveConfidenceFact",
    "ProgressionFacts",
    "PromotionContextFacts",
    "SelectionRationaleFacts",
    "SituationFacts",
    "assemble_lesson_facts",
    "slug_label",
)
