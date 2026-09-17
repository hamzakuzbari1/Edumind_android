"""Grammar Lesson Planner (G3.1) — sole authority for GrammarLessonBlueprint.

RESPONSIBILITY: Deterministic GrammarLessonBlueprint including ordered steps
(no LLM, no hardcoded skill chain, no execution, no mastery/progression writes).
Depends only on language_grammar_integration facade.
"""

from __future__ import annotations

from app.services.language_grammar_lesson_planner.builder import build_blueprint, disabled_blueprint
from app.services.language_grammar_lesson_planner.flags import (
    grammar_engine_enabled,
    grammar_engine_select_enabled,
)
from app.services.language_grammar_lesson_planner.serialization import (
    blueprint_from_dict,
    blueprint_to_dict,
)
from app.services.language_grammar_lesson_planner.service import plan_lesson, plan_lesson_via_facade
from app.services.language_grammar_lesson_planner.types import (
    GRAMMAR_BLUEPRINT_VERSION,
    GRAMMAR_PLANNER_VERSION,
    GRAMMAR_SCHEMA_VERSION,
    GrammarCompletionCriteria,
    GrammarEvidencePlan,
    GrammarLessonBlueprint,
    GrammarLessonStep,
    GrammarPlannerMetadata,
    GrammarPracticeSpec,
)
from app.services.language_grammar_lesson_planner.validation import (
    GrammarPlannerError,
    validate_blueprint,
    validate_snapshot_for_planning,
)

PACKAGE_VERSION = GRAMMAR_PLANNER_VERSION
RESPONSIBILITY = (
    "Deterministic GrammarLessonBlueprint including ordered steps "
    "(no LLM, no hardcoded skill chain)"
)

__all__ = [
    "GRAMMAR_BLUEPRINT_VERSION",
    "GRAMMAR_PLANNER_VERSION",
    "GRAMMAR_SCHEMA_VERSION",
    "GrammarCompletionCriteria",
    "GrammarEvidencePlan",
    "GrammarLessonBlueprint",
    "GrammarLessonStep",
    "GrammarPlannerError",
    "GrammarPlannerMetadata",
    "GrammarPracticeSpec",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "blueprint_from_dict",
    "blueprint_to_dict",
    "build_blueprint",
    "disabled_blueprint",
    "grammar_engine_enabled",
    "grammar_engine_select_enabled",
    "plan_lesson",
    "plan_lesson_via_facade",
    "validate_blueprint",
    "validate_snapshot_for_planning",
]
