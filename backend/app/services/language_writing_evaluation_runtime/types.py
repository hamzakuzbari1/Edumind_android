"""Evaluation & revision pipeline types (W7)."""



from __future__ import annotations



from dataclasses import dataclass



from app.services.language_writing_coach.types import WritingRevisionPlan

from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult

from app.services.language_writing_explainability.writing_narrative import WritingLearningNarrative

from app.services.language_writing_revision.types import WritingRevisionSession



EVALUATION_RUNTIME_VERSION = "8.1.0"





@dataclass(frozen=True, slots=True)

class EvaluationRevisionTurnResult:

    success: bool

    session: WritingRevisionSession

    evaluation: WritingEvaluationEngineResult

    narrative: WritingLearningNarrative

    revision_plan: WritingRevisionPlan

    completed: bool

    revision_number: int

    runtime_version: str = EVALUATION_RUNTIME_VERSION



    @property

    def comparison(self):

        return self.evaluation.comparison



    @property

    def evaluation_facts(self):

        """Legacy adapter."""

        return self.evaluation.to_evaluation_facts()



    @property

    def completion(self):

        """Legacy adapter for persistence/API."""

        return self.evaluation.completion



    def to_api_dict(self) -> dict[str, object]:

        return {

            "success": self.success,

            "completed": self.completed,

            "revision_number": self.revision_number,

            "lifecycle": self.session.lifecycle.value,

            "revision_plan": self.revision_plan.to_student_dict(),

            "ready_to_complete": self.evaluation.revision_readiness.ready,

            "completion": self.evaluation.completion.to_persistence_dict(),

            "comparison": self.comparison.to_persistence_dict() if self.comparison else None,

            "runtime_version": self.runtime_version,

        }
