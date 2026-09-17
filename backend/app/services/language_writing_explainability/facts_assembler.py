"""Writing facts assembler (W7) — canonical evaluation into WritingFactsBundle."""

from __future__ import annotations

from app.services.language_writing.enums import (
    ContextComplexity,
    OfficialWritingCEFR,
    WritingArc,
    WritingGoal,
    WritingLessonLifecycle,
)
from app.services.language_writing_evaluator.blueprint_snapshot import EvaluatorBlueprintSnapshot
from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult
from app.services.language_writing_explainability.types import (
    ContextComplexityFacts,
    WritingFactsBundle,
    WritingLessonFacts,
)


def assemble_writing_facts(
    *,
    blueprint: EvaluatorBlueprintSnapshot,
    evaluation: WritingEvaluationEngineResult,
    lifecycle: WritingLessonLifecycle = WritingLessonLifecycle.drafting,
    official_cefr: str | OfficialWritingCEFR = OfficialWritingCEFR.B1,
) -> WritingFactsBundle:
    """Assemble facts bundle from canonical evaluation — no educational decisions."""
    try:
        goal = WritingGoal(blueprint.personal_goal)
    except ValueError:
        goal = WritingGoal.general_english

    try:
        cefr = official_cefr if isinstance(official_cefr, OfficialWritingCEFR) else OfficialWritingCEFR(str(official_cefr))
    except ValueError:
        cefr = OfficialWritingCEFR.B1

    lesson = WritingLessonFacts(
        official_cefr=cefr,
        lesson_cefr=cefr,
        arc_stage=WritingArc.paragraph_writing,
        goal=goal,
        topic_id="",
        chain_id=blueprint.chain_id,
        chain_node_id=blueprint.chain_node_id,
        context_complexity=ContextComplexityFacts(
            level=ContextComplexity.everyday,
            label_internal="blueprint",
            student_label="everyday writing",
        ),
        lifecycle=lifecycle,
        weak_skills=evaluation.weak_skills[:4],
        grammar_focus=blueprint.grammar_primary,
        mission_why=blueprint.narrative_why,
        mission_goal=goal.value,
    )
    return WritingFactsBundle(lesson=lesson, evaluation=evaluation.to_coach_evaluation())
