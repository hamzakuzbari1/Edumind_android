"""Rich educational feedback after lesson completion (Priority 4)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing.enums import WritingGoal
from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult
from app.services.language_writing_explainability.student_evaluation_display import build_student_evaluation_display

COMPLETION_FEEDBACK_VERSION = "7.2.0"


@dataclass(frozen=True, slots=True)
class LessonCompletionFeedback:
    what_you_did_well: tuple[str, ...]
    mistakes_made: tuple[str, ...]
    why_mistakes_happened: tuple[str, ...]
    improve_next: tuple[str, ...]
    progress_change: str
    stage_proximity: str
    estimated_lessons_remaining: str
    journey_update: str
    history_comparison: tuple[str, ...] = ()
    feedback_version: str = COMPLETION_FEEDBACK_VERSION

    def to_student_dict(self) -> dict[str, object]:
        return {
            "what_you_did_well": list(self.what_you_did_well),
            "mistakes_made": list(self.mistakes_made),
            "why_mistakes_happened": list(self.why_mistakes_happened),
            "improve_next": list(self.improve_next),
            "progress_change": self.progress_change,
            "stage_proximity": self.stage_proximity,
            "estimated_lessons_remaining": self.estimated_lessons_remaining,
            "journey_update": self.journey_update,
            "history_comparison": list(self.history_comparison),
            "feedback_version": self.feedback_version,
        }


def build_lesson_completion_feedback(
    *,
    evaluation: WritingEvaluationEngineResult,
    official_cefr: str,
    goal: WritingGoal | str,
    chain_id: str,
    node_id: str,
    progression_state: dict | None = None,
    history_phrases: tuple[str, ...] = (),
) -> LessonCompletionFeedback:
    display = build_student_evaluation_display(evaluation)
    completion = evaluation.completion
    state = progression_state or {}
    lessons_count = int(state.get("lessons_completed_count") or 1)
    stage_label = str(state.get("learning_stage_label") or "Building foundations")
    estimated = int(state.get("estimated_lessons_to_next_stage") or 5)
    completed_nodes = len(state.get("completed_node_ids") or [])

    goal_label = goal.value.replace("_", " ") if isinstance(goal, WritingGoal) else str(goal).replace("_", " ")

    did_well = display.strengths or ("You finished a full writing cycle with coach feedback.",)
    mistakes = display.improvements or ("Keep strengthening task requirements.",)

    why: list[str] = []
    for w in evaluation.weak_skills[:3]:
        if w.startswith("grammar:"):
            why.append(f"Grammar focus '{w.split(':', 1)[-1]}' needs more practice in {goal_label} writing.")
        elif "vocabulary" in w:
            why.append("Topic vocabulary was not used consistently — the task expects specific words.")
        elif "word_count" in w:
            why.append("The draft was shorter than the blueprint minimum, so ideas were underdeveloped.")
        else:
            why.append(f"The task required more attention to {w.replace('_', ' ')}.")

    if not why:
        why.append("Small gaps in the success criteria checklist — review the coach mission for the next draft.")

    progress_change = (
        f"You completed node '{node_id}' on chain '{chain_id}'. "
        f"{completion.criteria_met_count} of {completion.criteria_total} success criteria met — "
        f"that means your draft addressed most of what this lesson required."
    )

    stage_proximity = (
        f"You are at {official_cefr.upper()} · {stage_label}. "
        f"After {lessons_count} completed writing lesson{'s' if lessons_count != 1 else ''}, "
        f"you have finished {completed_nodes} knowledge node{'s' if completed_nodes != 1 else ''}."
    )

    estimated_line = (
        f"About {estimated} more focused writing lesson{'s' if estimated != 1 else ''} "
        f"at this stage before you are ready for the next learning stage review."
    )

    journey_update = (
        f"Your {goal_label} journey moves forward — next lesson will target a new node matched to {official_cefr.upper()} "
        f"and your weak areas: {', '.join(list(display.improvements)[:2]) or 'continued practice'}."
    )

    return LessonCompletionFeedback(
        what_you_did_well=tuple(did_well),
        mistakes_made=tuple(mistakes),
        why_mistakes_happened=tuple(why),
        improve_next=tuple(display.improvements[:3]),
        progress_change=progress_change,
        stage_proximity=stage_proximity,
        estimated_lessons_remaining=estimated_line,
        journey_update=journey_update,
        history_comparison=history_phrases,
    )
