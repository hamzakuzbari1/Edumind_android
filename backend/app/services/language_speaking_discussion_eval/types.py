"""Types for the Discussion → S7 evaluation adapter (E4)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

DISCUSSION_EVAL_ADAPTER_VERSION = "1.0.0"


class DiscussionEvidenceCategory(StrEnum):
    """Configurable evidence categories — adapter mapping only, not S7 dimensions."""

    informational = "informational"
    vocabulary = "vocabulary"
    grammar = "grammar"
    communicative = "communicative"
    transfer = "transfer"


class DiscussionProductionMode(StrEnum):
    """How the student produced the response in discussion."""

    text = "text"
    spoken = "spoken"


class DiscussionEvalSkipReason(StrEnum):
    evidence_role_none = "evidence_role_none"
    role_not_eligible = "role_not_eligible"
    production_mode_blocked = "production_mode_blocked"
    empty_response = "empty_response"
    below_min_words = "below_min_words"
    no_step = "no_step"


@dataclass(frozen=True, slots=True)
class DiscussionEvalContext:
    """Minimum runtime context forwarded into packaging — never promotion/scores."""

    package_id: str
    discussion_id: str
    discussion_step_id: str
    question_id: str
    student_response: str
    lesson_objective_ref: str
    ladder_band: str
    evidence_role: str
    evidence_category: str
    production_mode: str


@dataclass(frozen=True, slots=True)
class DiscussionEvalHandoffResult:
    """Adapter outcome — never returned to the student UI."""

    adapter_version: str
    skipped: bool
    skip_reason: str | None
    evidence_category: str | None
    evaluation_id: str | None
    turn_reference: str | None
    session_id: str | None
    knowledge_mutation_status: str | None
    evidence_intent: str | None
    context: DiscussionEvalContext | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_version": self.adapter_version,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "evidence_category": self.evidence_category,
            "evaluation_id": self.evaluation_id,
            "turn_reference": self.turn_reference,
            "session_id": self.session_id,
            "knowledge_mutation_status": self.knowledge_mutation_status,
            "evidence_intent": self.evidence_intent,
            "context": None
            if self.context is None
            else {
                "package_id": self.context.package_id,
                "discussion_id": self.context.discussion_id,
                "discussion_step_id": self.context.discussion_step_id,
                "question_id": self.context.question_id,
                "student_response": self.context.student_response,
                "lesson_objective_ref": self.context.lesson_objective_ref,
                "ladder_band": self.context.ladder_band,
                "evidence_role": self.context.evidence_role,
                "evidence_category": self.context.evidence_category,
                "production_mode": self.context.production_mode,
            },
        }
