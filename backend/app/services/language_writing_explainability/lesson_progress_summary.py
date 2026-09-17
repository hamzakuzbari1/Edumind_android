"""Post-lesson progress summary (W7 UX) — render-only from canonical evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing.enums import WritingArc, WritingGoal
from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult
from app.services.language_writing_explainability.student_evaluation_display import build_student_evaluation_display

LESSON_PROGRESS_VERSION = "8.0.0"

_CEFR_STAGE: dict[str, str] = {
    "A1": "Sentence building",
    "A2": "Paragraph basics",
    "B1": "Paragraph writing",
    "B2": "Structured arguments",
    "C1": "Advanced formal writing",
    "C2": "Expert writing",
}

_ARC_LABELS: dict[str, str] = {
    WritingArc.sentence_building.value: "Sentence building",
    WritingArc.paragraph_writing.value: "Paragraph writing",
    WritingArc.narrative_writing.value: "Narrative writing",
    WritingArc.opinion_writing.value: "Opinion writing",
    WritingArc.formal_writing.value: "Formal writing",
    WritingArc.professional_writing.value: "Professional writing",
    WritingArc.academic_writing.value: "Academic writing",
}


@dataclass(frozen=True, slots=True)
class LessonProgressSummary:
    writing_stage_label: str
    progress_to_next_stage: str
    official_cefr: str
    improved_today: tuple[str, ...]
    focus_next: str
    progress_version: str = LESSON_PROGRESS_VERSION

    def to_student_dict(self) -> dict[str, object]:
        return {
            "writing_stage_label": self.writing_stage_label,
            "progress_to_next_stage": self.progress_to_next_stage,
            "official_cefr": self.official_cefr,
            "improved_today": list(self.improved_today),
            "focus_next": self.focus_next,
            "progress_version": self.progress_version,
        }


def build_lesson_progress_summary(
    *,
    evaluation: WritingEvaluationEngineResult,
    official_cefr: str,
    arc_stage: str,
    goal: WritingGoal | str,
    what_improved: tuple[str, ...] = (),
) -> LessonProgressSummary:
    display = build_student_evaluation_display(evaluation)
    completion = evaluation.completion
    stage = _ARC_LABELS.get(arc_stage, _CEFR_STAGE.get(official_cefr.upper(), "Writing practice"))
    writing_stage = f"{official_cefr.upper()} — {stage}"

    criteria_pct = 0
    if completion.criteria_total:
        criteria_pct = int(round(100 * completion.criteria_met_count / completion.criteria_total))
    progress_line = (
        f"{completion.criteria_met_count} of {completion.criteria_total} success criteria met "
        f"({criteria_pct}% toward this lesson's blueprint)."
    )

    improved = list(what_improved)
    improved.extend(display.strengths[:2])
    if not improved:
        improved.append("You completed a full write–evaluate–revise cycle.")

    focus = display.improvements[0] if display.improvements else "Keep revising with your goal vocabulary."
    goal_label = goal.value.replace("_", " ") if isinstance(goal, WritingGoal) else str(goal).replace("_", " ")

    return LessonProgressSummary(
        writing_stage_label=writing_stage,
        progress_to_next_stage=progress_line,
        official_cefr=official_cefr.upper(),
        improved_today=tuple(dict.fromkeys(improved)),
        focus_next=f"For your {goal_label} goal: {focus}",
    )
