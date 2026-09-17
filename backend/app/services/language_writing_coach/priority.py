"""Canonical educational priority selection (W7 Coach).

Single source of truth for the student's highest-value learning problem for the
next revision. It is chosen ONCE and then rendered by the coach, revision plan,
and completion feedback — none of them may independently pick another main issue.

Priority is EDUCATIONAL, not array-order based. An isolated local slip such as
"I are" must never outrank a deeper lesson target (e.g. question formation /
modal-verb control) that the lesson actually teaches.

This module produces educational guidance only. It NEVER decides
pass/fail/ready/complete/stage/readiness/promotion/official CEFR — those remain
owned by the Rule Engine and the progression engines.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.services.language_writing_educational_analyzer.types import (
    ClaudeEducationalFacts,
    CoachGuidance,
)
from app.services.language_writing_evaluator.evaluation_facts_types import CriterionStatus
from app.services.language_writing_evaluator.evaluation_result import WritingEvaluationEngineResult

logger = logging.getLogger(__name__)

PRIORITY_SELECTOR_VERSION = "1.0.0"

# Words that mark a success criterion as a word-count / length gate rather than a
# genuine grammar/vocabulary learning target.
_LENGTH_TOKENS = ("word", "words", "length", "at least", "minimum")


@dataclass(frozen=True, slots=True)
class CanonicalEducationalPriority:
    """The one learning priority for the next revision — rendered, never recomputed."""

    priority_key: str
    title: str
    why_it_matters: str
    revision_action: str
    example_before: str = ""
    example_after: str = ""
    student_explanation: str = ""
    encouragement: str = ""
    evidence: tuple[str, ...] = ()
    source: str = "canonical_fallback"  # "claude" | "canonical_fallback"

    def to_dict(self) -> dict[str, object]:
        return {
            "priority_key": self.priority_key,
            "title": self.title,
            "why_it_matters": self.why_it_matters,
            "revision_action": self.revision_action,
            "example_before": self.example_before,
            "example_after": self.example_after,
            "student_explanation": self.student_explanation,
            "encouragement": self.encouragement,
            "evidence": list(self.evidence),
            "source": self.source,
        }


def _target_labels(evaluation: WritingEvaluationEngineResult) -> tuple[str, ...]:
    """Unmet success criteria that are genuine learning targets (not length gates)."""
    out: list[str] = []
    for c in evaluation.success_criteria:
        if c.status == CriterionStatus.met:
            continue
        label = (c.label or "").strip()
        if not label:
            continue
        low = label.lower()
        if any(tok in low for tok in _LENGTH_TOKENS):
            continue
        out.append(label)
    return tuple(out)


def _join_labels(labels: tuple[str, ...], limit: int = 2) -> str:
    picked = labels[:limit]
    if not picked:
        return ""
    if len(picked) == 1:
        return picked[0]
    return f"{picked[0]} and {picked[1]}"


def _from_claude_guidance(
    guidance: CoachGuidance,
    claude: ClaudeEducationalFacts,
    evaluation: WritingEvaluationEngineResult,
) -> CanonicalEducationalPriority | None:
    """Build the canonical priority from Claude's validated coach guidance.

    Guidance is pre-validated in the parser (single distinct issue + mission, no
    progression decisions). Here we only fill any thin field from other Claude
    facts and derive a stable priority_key.
    """
    title = guidance.main_issue.strip()
    mission = guidance.revision_mission.strip()
    if not title or not mission:
        return None

    why = guidance.why_this_is_the_priority.strip() or claude.learning_diagnosis.strip()
    if not why:
        return None

    evidence: list[str] = []
    if guidance.before_example:
        evidence.append(guidance.before_example)
    for note in claude.grammar_notes[:2]:
        if note.example and note.example not in evidence:
            evidence.append(note.example)

    # Genuine LLM coaching is "claude"; heuristic (mock) guidance is deterministic.
    source = "claude" if claude.source == "claude" else "canonical_fallback"

    return CanonicalEducationalPriority(
        priority_key=_priority_key_for_issue(claude.major_learning_issue),
        title=title,
        why_it_matters=why,
        revision_action=mission,
        example_before=guidance.before_example,
        example_after=guidance.after_example,
        student_explanation=guidance.student_friendly_explanation or claude.learning_diagnosis,
        encouragement=guidance.encouragement or claude.encouragement,
        evidence=tuple(evidence[:4]),
        source=source,
    )


def _priority_key_for_issue(major_issue: str) -> str:
    low = (major_issue or "").lower()
    if "task" in low:
        return "task_response"
    if "topic" in low:
        return "topic_understanding"
    if "grammar" in low:
        return "target_grammar_control"
    if "vocab" in low:
        return "target_vocabulary"
    if "organi" in low or "coheren" in low:
        return "coherence_organization"
    if "idea" in low:
        return "idea_development"
    if "word count" in low:
        return "word_count"
    return "learning_target"


def _claude_reason(claude: ClaudeEducationalFacts | None, dim: str) -> str:
    if not claude or not claude.available:
        return ""
    insight = getattr(claude, dim, None)
    return getattr(insight, "reason", "") if insight else ""


def _canonical_fallback(
    evaluation: WritingEvaluationEngineResult,
    goal_label: str,
) -> CanonicalEducationalPriority:
    """Deterministic educational ladder — never the 'first grammar error'.

    Order (highest educational value first):
    1. task misunderstanding / off-topic
    2. failure to communicate the required task
    3. core lesson grammar targets
    4. core lesson vocabulary targets
    5. coherence / organization
    6. idea development
    7. repeated cross-draft mistake
    8. isolated local grammar / spelling slip
    """
    claude = evaluation.claude_analysis
    diagnosis = claude.learning_diagnosis.strip() if claude and claude.available else ""
    revision_priority = claude.revision_priority.strip() if claude and claude.available else ""
    encouragement = claude.encouragement.strip() if claude and claude.available else ""
    targets = _target_labels(evaluation)
    target_phrase = _join_labels(targets)

    tr = claude.task_response.score if claude and claude.available else None
    topic = claude.topic_understanding.score if claude and claude.available else None
    idea = claude.idea_development.score if claude and claude.available else None

    grammar_before = ""
    grammar_after = ""
    if claude and claude.available and claude.grammar_notes:
        grammar_before = claude.grammar_notes[0].issue
        grammar_after = claude.grammar_notes[0].fix or claude.grammar_notes[0].example

    # 1) Off-topic / task misunderstanding.
    off_topic = (
        (tr is not None and tr < 0.4)
        or (topic is not None and topic < 0.4)
        or (not evaluation.task_completion.passed and evaluation.task_completion.score < 0.4)
    )
    if off_topic:
        return CanonicalEducationalPriority(
            priority_key="task_response",
            title="Answer the actual question",
            why_it_matters=diagnosis
            or "Responding to the prompt is the priority — the rest only counts once the task is addressed.",
            revision_action=revision_priority
            or "Rewrite your opening so it directly answers what the prompt asked, then keep every sentence on that task.",
            student_explanation=_claude_reason(claude, "task_response")
            or "The draft does not yet answer the prompt directly.",
            encouragement=encouragement,
            evidence=tuple(evaluation.critical_mistakes[:3]),
            source="canonical_fallback",
        )

    # 2) Task not fully communicated.
    if not evaluation.task_completion.passed:
        return CanonicalEducationalPriority(
            priority_key="task_completion",
            title="Complete the full task",
            why_it_matters=diagnosis
            or "Covering every part of the task is the priority before polishing language.",
            revision_action=revision_priority
            or (
                f"Rewrite your draft so you clearly satisfy: {target_phrase}."
                if target_phrase
                else "Address each part of the task the prompt asked for."
            ),
            student_explanation=_claude_reason(claude, "task_response"),
            encouragement=encouragement,
            evidence=targets[:3],
            source="canonical_fallback",
        )

    # 3) Core lesson grammar targets.
    grammar_is_issue = (
        (claude and claude.available and "grammar" in claude.major_learning_issue.lower())
        or not evaluation.grammar.passed
    )
    if grammar_is_issue and (target_phrase or diagnosis):
        title = f"Accurate {target_phrase}" if target_phrase else "Grammar control in this lesson's target structures"
        return CanonicalEducationalPriority(
            priority_key="target_grammar_control",
            title=title,
            why_it_matters=diagnosis
            or f"These are the grammar targets of this lesson and {target_phrase or 'the key structures'} are still inaccurate.",
            revision_action=revision_priority
            or (
                f"Rewrite each sentence that uses {target_phrase}, checking the structure is accurate."
                if target_phrase
                else "Rewrite the sentences with the lesson's target grammar, checking each structure carefully."
            ),
            example_before=grammar_before,
            example_after=grammar_after,
            student_explanation=diagnosis,
            encouragement=encouragement,
            evidence=tuple(evaluation.grammar.errors[:3]),
            source="canonical_fallback",
        )

    # 4) Core lesson vocabulary targets.
    vocab_is_issue = (
        (claude and claude.available and "vocab" in claude.major_learning_issue.lower())
        or not evaluation.vocabulary.passed
    )
    if vocab_is_issue:
        return CanonicalEducationalPriority(
            priority_key="target_vocabulary",
            title="Stronger, more varied vocabulary",
            why_it_matters=diagnosis
            or "Wider word choice is the priority — repeated or vague words are limiting the message.",
            revision_action=revision_priority
            or "Replace your most repeated words with more precise topic vocabulary.",
            student_explanation=_claude_reason(claude, "vocabulary"),
            encouragement=encouragement,
            evidence=tuple(evaluation.vocabulary.errors[:3]),
            source="canonical_fallback",
        )

    # 5) Coherence / organization.
    if not evaluation.organization.passed:
        return CanonicalEducationalPriority(
            priority_key="coherence_organization",
            title="Clearer organization and flow",
            why_it_matters=diagnosis
            or "Clear structure is the priority so the reader can follow your ideas easily.",
            revision_action=revision_priority
            or "Group related ideas into paragraphs and add linking words between them.",
            student_explanation=_claude_reason(claude, "organization") or _claude_reason(claude, "coherence"),
            encouragement=encouragement,
            evidence=tuple(evaluation.organization.errors[:3]),
            source="canonical_fallback",
        )

    # 6) Idea development.
    if idea is not None and idea < 0.5:
        return CanonicalEducationalPriority(
            priority_key="idea_development",
            title="Develop and support your ideas",
            why_it_matters=diagnosis
            or "Explaining ideas with examples is what moves your writing up a level.",
            revision_action=revision_priority or "Support each main point with one concrete example.",
            student_explanation=_claude_reason(claude, "idea_development"),
            encouragement=encouragement,
            source="canonical_fallback",
        )

    # 7) Repeated cross-draft mistake.
    if evaluation.comparison and (evaluation.comparison.regressed or evaluation.comparison.remaining_issues):
        remaining = evaluation.comparison.remaining_issues or evaluation.comparison.regressed
        return CanonicalEducationalPriority(
            priority_key="repeated_mistake",
            title="Fix the mistake that keeps returning",
            why_it_matters=diagnosis
            or "This issue appeared in your previous draft too — clearing it now unlocks real progress.",
            revision_action=revision_priority
            or f"Focus this revision on removing: {_join_labels(tuple(remaining))}.",
            student_explanation=diagnosis,
            encouragement=encouragement,
            evidence=tuple(remaining[:3]),
            source="canonical_fallback",
        )

    # 8) Isolated local grammar / spelling slip (LAST — never the headline when a
    # deeper lesson issue exists).
    if evaluation.grammar.errors:
        return CanonicalEducationalPriority(
            priority_key="local_accuracy",
            title="Polish a few remaining accuracy slips",
            why_it_matters=diagnosis
            or "Your writing is largely on track — a final accuracy pass will make it clean.",
            revision_action=revision_priority
            or "Proofread each sentence and correct the small grammar and spelling slips.",
            example_before=grammar_before or (evaluation.grammar.errors[0] if evaluation.grammar.errors else ""),
            example_after=grammar_after,
            student_explanation=diagnosis,
            encouragement=encouragement,
            evidence=tuple(evaluation.grammar.errors[:3]),
            source="canonical_fallback",
        )

    # 9) Default polish.
    return CanonicalEducationalPriority(
        priority_key="general_polish",
        title="Refine and extend your draft",
        why_it_matters=diagnosis
        or "The core is solid — the priority now is to extend and sharpen your ideas.",
        revision_action=revision_priority
        or f"Add one more well-developed idea that fits your {goal_label.lower() or 'writing'} goal.",
        student_explanation=diagnosis,
        encouragement=encouragement,
        source="canonical_fallback",
    )


def select_educational_priority(
    *,
    evaluation: WritingEvaluationEngineResult,
    goal_label: str = "",
) -> CanonicalEducationalPriority:
    """Pick the single highest-value learning priority for the next revision.

    Prefers Claude's validated coach guidance; otherwise falls back to the
    deterministic educational ladder. Never falls back to the 'first grammar
    error'. The chosen source is logged.
    """
    claude = evaluation.claude_analysis
    if claude and claude.available and claude.coach_guidance.available:
        priority = _from_claude_guidance(claude.coach_guidance, claude, evaluation)
        if priority is not None:
            logger.info(
                "writing coach priority source=%s key=%s",
                priority.source,
                priority.priority_key,
            )
            return priority
        logger.warning(
            "writing coach guidance present but unusable; using canonical fallback"
        )

    priority = _canonical_fallback(evaluation, goal_label)
    logger.info(
        "writing coach priority source=canonical_fallback key=%s", priority.priority_key
    )
    return priority
