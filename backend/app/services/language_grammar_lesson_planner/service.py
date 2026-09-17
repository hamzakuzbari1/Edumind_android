"""Grammar Lesson Planner service (G3.1) — Blueprint only; no execution."""

from __future__ import annotations

from app.services.language_grammar_integration.service import GrammarIntegrationService
from app.services.language_grammar_integration.types import GrammarLearningSnapshot
from app.services.language_grammar_lesson_planner.builder import build_blueprint, disabled_blueprint
from app.services.language_grammar_lesson_planner.flags import (
    grammar_engine_enabled,
    grammar_engine_select_enabled,
)
from app.services.language_grammar_lesson_planner.types import GrammarLessonBlueprint


def plan_lesson(snapshot: GrammarLearningSnapshot) -> GrammarLessonBlueprint:
    """Plan from a GrammarLearningSnapshot (produced by Integration facade)."""
    if not grammar_engine_enabled() or not snapshot.enabled:
        return disabled_blueprint(
            grammar_id=snapshot.current_grammar_id or "",
            reason="flag:LANG_GRAMMAR_ENGINE_ENABLED=false",
        )
    return build_blueprint(snapshot)


def plan_lesson_via_facade(
    *,
    student_id: int,
    language_id: int,
    overall_cefr,
    progression,
    mastery,
    as_of: str,
    fatigue_budget_minutes: int = 45,
) -> GrammarLessonBlueprint:
    """Build snapshot via GrammarIntegrationService then plan — no direct engine imports."""
    snapshot = GrammarIntegrationService.build_learning_snapshot_for_planner(
        student_id=student_id,
        language_id=language_id,
        overall_cefr=overall_cefr,
        progression=progression,
        mastery=mastery,
        as_of=as_of,
        fatigue_budget_minutes=fatigue_budget_minutes,
    )
    if not grammar_engine_select_enabled():
        # SELECT off: still allow blueprint compute for tests; selection already nulled by facade
        pass
    return plan_lesson(snapshot)
