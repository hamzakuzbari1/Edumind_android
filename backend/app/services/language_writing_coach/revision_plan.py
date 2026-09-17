"""Revision plan contracts (W2) — coach output structure."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_writing.enums import WritingCoachPersonality
from app.services.language_writing_coach.types import WritingFeedback, WritingRevisionPlan


def revision_plan_to_feedback(plan: WritingRevisionPlan) -> WritingFeedback:
    """Map canonical revision plan to legacy WritingFeedback contract."""
    return WritingFeedback(
        what_improved=plan.what_improved,
        main_weakness=plan.main_issue,
        priority_fix=plan.priority_fix,
        concrete_example=plan.concrete_example,
        encouragement=plan.encouragement,
        next_focus=plan.next_lesson_recommendation,
        ready_to_complete=plan.ready_to_complete,
        personality=plan.personality,
    )


def feedback_fields_complete(plan: WritingRevisionPlan) -> bool:
    """Validate W2 revision plan has all required student-facing fields."""
    return bool(
        plan.encouragement.strip()
        and plan.main_issue.strip()
        and plan.priority_fix.strip()
        and plan.concrete_example.strip()
        and plan.revision_mission.strip()
        and plan.next_lesson_recommendation.strip()
    )
