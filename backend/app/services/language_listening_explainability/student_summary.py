"""Student summary legacy adapter entry (Phase 2.1)."""

from __future__ import annotations

from app.services.language_learning_facts.assembler import (
    assemble_challenge_facts,
    assemble_curriculum_facts,
    assemble_goal_facts,
    assemble_level_context_facts,
    assemble_situation_facts,
)
from app.services.language_learning_facts.types import LessonFactsBundle
from app.services.language_learning_narrative.builder import build_lesson_narrative
from app.services.language_learning_narrative.legacy_adapter import legacy_student_summary
from app.services.language_listening_confidence.types import ConfidenceState
from app.services.language_listening_explainability.facts import build_explainability_facts
from app.services.language_listening_explainability.types import ExplainabilitySignals, LessonExplainability, StudentSummary


def build_student_summary(
    signals: ExplainabilitySignals,
    lesson: LessonExplainability,
    *,
    confidence_state: ConfidenceState | None,
) -> StudentSummary:
    """Legacy compatibility — narrative builder owns student copy."""
    del lesson  # narrative is rebuilt from facts; lesson arg kept for API stability
    lesson_facts = LessonFactsBundle(
        lesson_id=None,
        lesson_title=None,
        lesson_type="practice",
        question_types=signals.question_types,
        situation=assemble_situation_facts(signals),
        curriculum=assemble_curriculum_facts(signals),
        goal=assemble_goal_facts(signals),
        challenge=assemble_challenge_facts(signals),
        level=assemble_level_context_facts(signals),
    )
    explain = build_explainability_facts(signals, confidence_state=confidence_state)
    narrative = build_lesson_narrative(lesson_facts, explain)
    return legacy_student_summary(narrative, explain, confidence_state=confidence_state)
