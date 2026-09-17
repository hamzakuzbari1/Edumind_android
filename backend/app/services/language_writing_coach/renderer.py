"""Writing Coach renderer (W7) — render-only from canonical evaluation."""

from __future__ import annotations

from app.services.language_writing.enums import WritingCoachPersonality, WritingGoal
from app.services.language_writing_coach.adaptive_tone import AdaptiveToneContext, AdaptiveToneAdjustment
from app.services.language_writing_coach.personalities import profile_for_personality
from app.services.language_writing_coach.priority import CanonicalEducationalPriority
from app.services.language_writing_coach.revision_plan import feedback_fields_complete
from app.services.language_writing_coach.types import CoachInputBundle, CoachNarrativeContext, WritingRevisionPlan
from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult

COACH_RENDERER_VERSION = "8.0.0"

_GOAL_NEXT_LESSON: dict[WritingGoal, str] = {
    WritingGoal.travel: "Next, practice a travel review or a polite hotel complaint email.",
    WritingGoal.business: "Next, write a short workplace email or meeting request.",
    WritingGoal.ielts: "Next, continue with another IELTS Task 2 opinion paragraph.",
    WritingGoal.general_english: "Next, keep practicing everyday paragraphs and short messages.",
    WritingGoal.academic: "Next, try a short academic paragraph with clear topic sentences.",
    WritingGoal.job_interview: "Next, draft a professional introduction or cover letter paragraph.",
    WritingGoal.daily_communication: "Next, practice a clear message for a daily situation.",
    WritingGoal.creative_writing: "Next, expand a creative story opening with vivid details.",
}


def _encouragement_prefix(personality: WritingCoachPersonality, tone: AdaptiveToneContext) -> str:
    profile = profile_for_personality(personality)
    base = profile.encouragement_style
    if AdaptiveToneAdjustment.celebrate_progress in tone.adjustments:
        return f"{base} — nice progress this turn."
    if AdaptiveToneAdjustment.more_patience in tone.adjustments:
        return f"{base} — take your time with the next revision."
    return base


def _goal_recommendation(goal: WritingGoal) -> str:
    return _GOAL_NEXT_LESSON.get(
        goal,
        "Next, generate another writing mission aligned with your personal goal.",
    )


def _concrete_example(priority: CanonicalEducationalPriority) -> str:
    """One example line for legacy consumers — before → after when both exist."""
    if priority.example_before and priority.example_after:
        return f"{priority.example_before} → {priority.example_after}"
    if priority.example_before:
        return priority.example_before
    if priority.example_after:
        return priority.example_after
    return priority.student_explanation or priority.why_it_matters


def render_revision_plan(
    bundle: CoachInputBundle,
    narrative: CoachNarrativeContext,
    *,
    evaluation: WritingEvaluationEngineResult,
    priority: CanonicalEducationalPriority,
    personality: WritingCoachPersonality,
    revision_turn: int,
    tone: AdaptiveToneContext | None = None,
    what_improved: tuple[str, ...] = (),
    history_phrases: tuple[str, ...] = (),
) -> WritingRevisionPlan:
    """Render the student-facing revision plan — RENDER ONLY.

    The coach does not select the weakness, the priority, the mission, or the
    example. It renders the single canonical educational priority chosen upstream.
    Each field carries a distinct educational purpose:
    - main_issue        = the one learning problem (WHAT)
    - why_it_matters    = why this is the priority now (WHY)
    - revision_mission  = the one action that repairs it (HOW)
    - before/after      = a concrete demonstration of the same issue (SHOW)
    - encouragement     = specific, warm motivation
    """
    tone_ctx = tone or AdaptiveToneContext.resolve(personality=personality, triggers=())
    next_lesson = _goal_recommendation(bundle.goal_profile.goal)

    # Encouragement: prefer the priority's specific line, wrapped in coach tone.
    if priority.encouragement:
        encouragement = priority.encouragement
        if history_phrases:
            encouragement = f"{encouragement} {history_phrases[0]}"
    else:
        encouragement = _encouragement_prefix(personality, tone_ctx)
        if history_phrases:
            encouragement = f"{encouragement} {history_phrases[0]}"
        elif what_improved:
            encouragement = f"{encouragement} You improved: {what_improved[0]}."

    why_it_matters = priority.why_it_matters or priority.student_explanation

    plan = WritingRevisionPlan(
        encouragement=encouragement,
        main_issue=priority.title,
        priority_fix=why_it_matters,
        concrete_example=_concrete_example(priority),
        revision_mission=priority.revision_action,
        why_it_matters=why_it_matters,
        before_example=priority.example_before,
        after_example=priority.example_after,
        priority_key=priority.priority_key,
        guidance_source=priority.source,
        ready_to_complete=evaluation.revision_readiness.ready,
        next_lesson_recommendation=next_lesson,
        what_improved=what_improved,
        personality=personality,
        revision_turn=revision_turn,
        coach_version=COACH_RENDERER_VERSION,
    )
    if not feedback_fields_complete(plan):
        raise ValueError("Coach revision plan missing required fields")
    return plan
