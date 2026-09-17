"""Types for Writing Revision Loop (W0/W2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.services.language_writing.enums import WritingLessonLifecycle, WritingRevisionStatus
from app.services.language_writing_coach.types import WritingFeedback, WritingRevisionPlan


class RevisionWorkflowStage(StrEnum):
    """W2 revision workflow stages — orchestration contract only."""

    draft_submitted = "draft_submitted"
    evaluating = "evaluating"
    facts_ready = "facts_ready"
    narrative_ready = "narrative_ready"
    coach_plan_ready = "coach_plan_ready"
    awaiting_student_revision = "awaiting_student_revision"
    resubmitted = "resubmitted"
    coach_approved_complete = "coach_approved_complete"


@dataclass(frozen=True, slots=True)
class WritingDraft:
    """Single draft submission."""

    draft_id: str
    attempt_number: int
    text: str
    word_count: int
    submitted_at: str
    revision_status: WritingRevisionStatus = WritingRevisionStatus.pending_coach


@dataclass(frozen=True, slots=True)
class WritingRevision:
    """Coach turn linked to a draft pair (before → after)."""

    revision_id: str
    from_draft_id: str
    to_draft_id: str | None
    feedback: WritingFeedback
    revision_plan: WritingRevisionPlan | None = None
    workflow_stage: RevisionWorkflowStage = RevisionWorkflowStage.coach_plan_ready
    created_at: str = ""


@dataclass
class WritingRevisionSession:
    """Full revision session for one lesson."""

    student_id: int
    content_item_id: int
    lifecycle: WritingLessonLifecycle = WritingLessonLifecycle.not_started
    drafts: list[WritingDraft] = field(default_factory=list)
    revisions: list[WritingRevision] = field(default_factory=list)
    first_draft_id: str | None = None
    final_draft_id: str | None = None
    completed_at: str | None = None

    @property
    def latest_draft(self) -> WritingDraft | None:
        return self.drafts[-1] if self.drafts else None

    @property
    def latest_feedback(self) -> WritingFeedback | None:
        return self.revisions[-1].feedback if self.revisions else None
