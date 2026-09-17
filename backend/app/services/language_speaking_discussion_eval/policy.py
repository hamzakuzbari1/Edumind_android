"""Configurable discussion → evidence eligibility policy (E4).

Does not score. Does not mutate knowledge. Only decides whether a turn may
be forwarded to the existing S7 evaluation runtime.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_educational_package.evidence_policy import DiscussionEvidenceRole
from app.services.language_educational_package.question_ladder import QuestionBand
from app.services.language_educational_package.types import DiscussionStep
from app.services.language_speaking.enums import SpeakingEvidenceIntent
from app.services.language_speaking_discussion_eval.types import (
    DiscussionEvidenceCategory,
    DiscussionEvalSkipReason,
    DiscussionProductionMode,
)

# Roles that may become evidence when production mode is allowed.
DEFAULT_ELIGIBLE_ROLES: frozenset[DiscussionEvidenceRole] = frozenset(
    {
        DiscussionEvidenceRole.formative_light,
        DiscussionEvidenceRole.formative,
        DiscussionEvidenceRole.transfer,
    }
)

# Text chat may produce formative/transfer evidence (SPA-style transcript path).
# Spoken-only tightening can clear roles from this set without changing S7.
DEFAULT_TEXT_ELIGIBLE_ROLES: frozenset[DiscussionEvidenceRole] = frozenset(
    {
        DiscussionEvidenceRole.formative_light,
        DiscussionEvidenceRole.formative,
        DiscussionEvidenceRole.transfer,
    }
)

DEFAULT_SPOKEN_ELIGIBLE_ROLES: frozenset[DiscussionEvidenceRole] = frozenset(
    {
        DiscussionEvidenceRole.formative_light,
        DiscussionEvidenceRole.formative,
        DiscussionEvidenceRole.transfer,
    }
)

# Reliability hint passed into SpeakingEvaluationInput (adapter packaging only).
DEFAULT_RELIABILITY_BY_ROLE: dict[DiscussionEvidenceRole, float] = {
    DiscussionEvidenceRole.none: 0.0,
    DiscussionEvidenceRole.formative_light: 0.45,
    DiscussionEvidenceRole.formative: 0.65,
    DiscussionEvidenceRole.transfer: 0.7,
}

DEFAULT_MIN_WORDS_BY_ROLE: dict[DiscussionEvidenceRole, int] = {
    DiscussionEvidenceRole.none: 0,
    DiscussionEvidenceRole.formative_light: 2,
    DiscussionEvidenceRole.formative: 3,
    DiscussionEvidenceRole.transfer: 4,
}


def category_for_step(step: DiscussionStep) -> DiscussionEvidenceCategory:
    """Map step role + ladder band into a configurable evidence category."""
    role = step.evidence_role
    if role == DiscussionEvidenceRole.none:
        return DiscussionEvidenceCategory.informational
    if role == DiscussionEvidenceRole.transfer:
        return DiscussionEvidenceCategory.transfer
    band = step.ladder_band
    if band == QuestionBand.vocabulary or (
        role == DiscussionEvidenceRole.formative_light and step.vocabulary_ids and not step.grammar_topic_ids
    ):
        return DiscussionEvidenceCategory.vocabulary
    if band == QuestionBand.grammar_in_context or (
        role == DiscussionEvidenceRole.formative_light and step.grammar_topic_ids
    ):
        return DiscussionEvidenceCategory.grammar
    return DiscussionEvidenceCategory.communicative


def evidence_intent_for_role(role: DiscussionEvidenceRole) -> SpeakingEvidenceIntent:
    if role == DiscussionEvidenceRole.transfer:
        return SpeakingEvidenceIntent.transfer
    if role in {DiscussionEvidenceRole.formative, DiscussionEvidenceRole.formative_light}:
        return SpeakingEvidenceIntent.formative
    return SpeakingEvidenceIntent.none


@dataclass(frozen=True, slots=True)
class DiscussionEvalPolicyDecision:
    eligible: bool
    skip_reason: DiscussionEvalSkipReason | None
    category: DiscussionEvidenceCategory
    evidence_intent: SpeakingEvidenceIntent
    reliability: float
    min_words: int


@dataclass(frozen=True, slots=True)
class DiscussionEvalPolicy:
    """Override maps/sets to reconfigure without modifying S7."""

    eligible_roles: frozenset[DiscussionEvidenceRole] = DEFAULT_ELIGIBLE_ROLES
    text_eligible_roles: frozenset[DiscussionEvidenceRole] = DEFAULT_TEXT_ELIGIBLE_ROLES
    spoken_eligible_roles: frozenset[DiscussionEvidenceRole] = DEFAULT_SPOKEN_ELIGIBLE_ROLES
    reliability_by_role: dict[DiscussionEvidenceRole, float] | None = None
    min_words_by_role: dict[DiscussionEvidenceRole, int] | None = None

    def decide(
        self,
        step: DiscussionStep | None,
        *,
        student_response: str,
        production_mode: DiscussionProductionMode = DiscussionProductionMode.text,
    ) -> DiscussionEvalPolicyDecision:
        reliability_map = self.reliability_by_role or DEFAULT_RELIABILITY_BY_ROLE
        min_words_map = self.min_words_by_role or DEFAULT_MIN_WORDS_BY_ROLE

        if step is None:
            return DiscussionEvalPolicyDecision(
                eligible=False,
                skip_reason=DiscussionEvalSkipReason.no_step,
                category=DiscussionEvidenceCategory.informational,
                evidence_intent=SpeakingEvidenceIntent.none,
                reliability=0.0,
                min_words=0,
            )

        category = category_for_step(step)
        role = step.evidence_role
        intent = evidence_intent_for_role(role)
        reliability = float(reliability_map.get(role, 0.0))
        min_words = int(min_words_map.get(role, 0))

        text = (student_response or "").strip()
        if not text:
            return DiscussionEvalPolicyDecision(
                eligible=False,
                skip_reason=DiscussionEvalSkipReason.empty_response,
                category=category,
                evidence_intent=intent,
                reliability=reliability,
                min_words=min_words,
            )

        if role == DiscussionEvidenceRole.none or category == DiscussionEvidenceCategory.informational:
            return DiscussionEvalPolicyDecision(
                eligible=False,
                skip_reason=DiscussionEvalSkipReason.evidence_role_none,
                category=DiscussionEvidenceCategory.informational,
                evidence_intent=SpeakingEvidenceIntent.none,
                reliability=0.0,
                min_words=min_words,
            )

        if role not in self.eligible_roles:
            return DiscussionEvalPolicyDecision(
                eligible=False,
                skip_reason=DiscussionEvalSkipReason.role_not_eligible,
                category=category,
                evidence_intent=intent,
                reliability=reliability,
                min_words=min_words,
            )

        mode_roles = (
            self.spoken_eligible_roles
            if production_mode == DiscussionProductionMode.spoken
            else self.text_eligible_roles
        )
        if role not in mode_roles:
            return DiscussionEvalPolicyDecision(
                eligible=False,
                skip_reason=DiscussionEvalSkipReason.production_mode_blocked,
                category=category,
                evidence_intent=intent,
                reliability=reliability,
                min_words=min_words,
            )

        word_count = len(text.split())
        if word_count < min_words:
            return DiscussionEvalPolicyDecision(
                eligible=False,
                skip_reason=DiscussionEvalSkipReason.below_min_words,
                category=category,
                evidence_intent=intent,
                reliability=reliability,
                min_words=min_words,
            )

        return DiscussionEvalPolicyDecision(
            eligible=True,
            skip_reason=None,
            category=category,
            evidence_intent=intent,
            reliability=reliability,
            min_words=min_words,
        )


DEFAULT_DISCUSSION_EVAL_POLICY = DiscussionEvalPolicy()
