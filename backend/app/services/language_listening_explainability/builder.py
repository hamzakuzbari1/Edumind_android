"""Explainability builder compatibility layer (Phase 3.4 / 2.1)."""

from __future__ import annotations

from app.services.language_listening_explainability.signals import (
    EXPECTED_SIGNALS,
    extract_signals,
    top_score_factors,
)

__all__ = ("EXPECTED_SIGNALS", "extract_signals", "top_score_factors", "build_lesson_explainability")


def build_lesson_explainability(signals):
    """Legacy compatibility — facts → narrative → LessonExplainability."""
    from app.services.language_learning_facts.assembler import (
        assemble_challenge_facts,
        assemble_curriculum_facts,
        assemble_goal_facts,
        assemble_level_context_facts,
        assemble_situation_facts,
    )
    from app.services.language_learning_facts.types import LessonFactsBundle
    from app.services.language_learning_narrative.builder import build_lesson_narrative
    from app.services.language_learning_narrative.legacy_adapter import legacy_lesson_explainability
    from app.services.language_listening_explainability.facts import build_explainability_facts

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
    explain = build_explainability_facts(signals)
    narrative = build_lesson_narrative(lesson_facts, explain)
    return legacy_lesson_explainability(narrative, explain)
