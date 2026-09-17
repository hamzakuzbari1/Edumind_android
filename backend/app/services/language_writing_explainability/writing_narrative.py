"""Writing Learning Narrative (W7) — student-facing copy from canonical evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult
from app.services.language_writing_explainability.types import WritingFactsBundle

NARRATIVE_VERSION = "8.0.0"


@dataclass(frozen=True, slots=True)
class WritingLearningNarrative:
    coach_summary: str
    focus_sentence: str
    improvement_context: str
    strengths_summary: str
    priority_area: str
    narrative_version: str = NARRATIVE_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "coach_summary": self.coach_summary,
            "focus_sentence": self.focus_sentence,
            "improvement_context": self.improvement_context,
            "strengths_summary": self.strengths_summary,
            "priority_area": self.priority_area,
            "narrative_version": self.narrative_version,
        }


def build_writing_learning_narrative(
    facts_bundle: WritingFactsBundle,
    evaluation: WritingEvaluationEngineResult,
) -> WritingLearningNarrative:
    """Build narrative from canonical evaluation — no score computation."""
    expl = evaluation.explanation
    strengths = ", ".join(evaluation.strong_skills[:3]) or "clear effort on the task"
    return WritingLearningNarrative(
        coach_summary=expl.summary,
        focus_sentence=f"Today's focus: {expl.focus_label}",
        improvement_context=f"Priority improvement area: {expl.focus_label}",
        strengths_summary=f"Strengths observed: {strengths}",
        priority_area=expl.focus_label,
    )
