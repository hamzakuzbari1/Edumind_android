"""Student-safe speaking session summary — render-only from canonical S7 evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_speaking_evaluator.evaluation_result import SpeakingEvaluationEngineResult

SPEAKING_STUDENT_SESSION_SUMMARY_VERSION = "0.1.0"

_DIMENSION_LABELS = {
    "task_response": "Task Response",
    "topic_understanding": "Topic Understanding",
    "pronunciation": "Pronunciation",
    "fluency_delivery": "Fluency & Delivery",
    "grammar": "Grammar",
    "vocabulary": "Vocabulary",
    "coherence": "Coherence",
    "interaction": "Interaction",
    "goal_alignment": "Goal Alignment",
}


def _dimension_status(passed: bool) -> str:
    return "on_track" if passed else "needs_work"


@dataclass(frozen=True, slots=True)
class SpeakingStudentSessionSummary:
    """Post-turn student summary — no scores, IDs, or internal weights."""

    coach_summary: str
    focus_label: str
    priority_issue: str
    strengths: tuple[str, ...]
    improvements: tuple[str, ...]
    dimensions: tuple[dict[str, object], ...]
    since_last_time: str
    ready_to_continue: bool
    can_complete: bool
    completion_note: str
    display_version: str = SPEAKING_STUDENT_SESSION_SUMMARY_VERSION

    def to_student_dict(self) -> dict[str, object]:
        return {
            "coach_summary": self.coach_summary,
            "focus_label": self.focus_label,
            "priority_issue": self.priority_issue,
            "strengths": list(self.strengths),
            "improvements": list(self.improvements),
            "dimensions": list(self.dimensions),
            "since_last_time": self.since_last_time,
            "ready_to_continue": self.ready_to_continue,
            "can_complete": self.can_complete,
            "completion_note": self.completion_note,
            "display_version": self.display_version,
        }


def build_speaking_student_session_summary(
    evaluation: SpeakingEvaluationEngineResult,
) -> SpeakingStudentSessionSummary:
    """Build student session summary — render-only from canonical evaluation."""
    expl = evaluation.explanation
    dimensions = tuple(
        {
            "key": dim.dimension,
            "label": _DIMENSION_LABELS.get(
                dim.dimension,
                dim.dimension.replace("_", " ").title(),
            ),
            "status": _dimension_status(dim.passed),
            "reason": dim.reason,
        }
        for dim in (
            evaluation.task_response,
            evaluation.topic_understanding,
            evaluation.pronunciation,
            evaluation.fluency_delivery,
            evaluation.grammar,
            evaluation.vocabulary,
            evaluation.coherence,
            evaluation.interaction,
            evaluation.goal_alignment,
        )
    )
    return SpeakingStudentSessionSummary(
        coach_summary=expl.summary,
        focus_label=expl.focus_label,
        priority_issue=expl.priority_issue,
        strengths=expl.strengths[:3],
        improvements=expl.improvements[:3],
        dimensions=dimensions,
        since_last_time=evaluation.comparison_with_previous_attempt,
        ready_to_continue=evaluation.revision_readiness.ready,
        can_complete=evaluation.completion_eligibility.eligible,
        completion_note=evaluation.completion_eligibility.reason,
    )
