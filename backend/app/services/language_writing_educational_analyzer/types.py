"""Structured educational facts from Claude — deep analysis only, never pass/fail.

The analyzer understands a draft like an experienced English teacher: meaning,
communication, educational quality, and language ability. It NEVER decides
pass/fail/ready/complete/promotion/stage — those remain owned by the Rule Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ANALYZER_FACTS_VERSION = "2.0.0"


@dataclass(frozen=True, slots=True)
class DimensionInsight:
    """One educational dimension: a 0–1 quality signal plus a teacher explanation."""

    score: float
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"score": round(self.score, 4), "reason": self.reason}


@dataclass(frozen=True, slots=True)
class GrammarNote:
    """One grammar issue explained like a teacher: what, why, how to fix, example."""

    issue: str
    rule: str = ""
    fix: str = ""
    example: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"issue": self.issue, "rule": self.rule, "fix": self.fix, "example": self.example}

    def to_feedback_line(self) -> str:
        parts = [self.issue]
        if self.rule:
            parts.append(f"Rule: {self.rule}")
        if self.fix:
            parts.append(f"Fix: {self.fix}")
        if self.example:
            parts.append(f"Example: {self.example}")
        return " — ".join(parts)


@dataclass(frozen=True, slots=True)
class VocabularyInsight:
    """Vocabulary analysis: range, repetition, weak choices, missing topic words."""

    score: float
    reason: str = ""
    range_comment: str = ""
    repeated_words: tuple[str, ...] = ()
    weak_choices: tuple[str, ...] = ()
    missing_topic_words: tuple[str, ...] = ()
    suggestions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "score": round(self.score, 4),
            "reason": self.reason,
            "range_comment": self.range_comment,
            "repeated_words": list(self.repeated_words),
            "weak_choices": list(self.weak_choices),
            "missing_topic_words": list(self.missing_topic_words),
            "suggestions": list(self.suggestions),
        }


@dataclass(frozen=True, slots=True)
class CoachGuidance:
    """One coherent teacher coaching plan for the next revision.

    Educational guidance only — never a pass/fail/ready/promotion decision. Each
    field has a distinct purpose so the Coach UI never repeats the same sentence.
    """

    main_issue: str = ""
    why_this_is_the_priority: str = ""
    revision_mission: str = ""
    student_friendly_explanation: str = ""
    before_example: str = ""
    after_example: str = ""
    encouragement: str = ""
    available: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "main_issue": self.main_issue,
            "why_this_is_the_priority": self.why_this_is_the_priority,
            "revision_mission": self.revision_mission,
            "student_friendly_explanation": self.student_friendly_explanation,
            "before_example": self.before_example,
            "after_example": self.after_example,
            "encouragement": self.encouragement,
            "available": self.available,
        }


def _empty_insight() -> DimensionInsight:
    return DimensionInsight(0.0, "")


def _empty_vocab() -> VocabularyInsight:
    return VocabularyInsight(0.0, "")


def _empty_coach_guidance() -> "CoachGuidance":
    return CoachGuidance()


@dataclass(frozen=True, slots=True)
class ClaudeEducationalFacts:
    """Deep educational analysis from Claude — must not contain pass/fail or ready flags.

    Dimensions mirror an experienced teacher's read of a draft. Every judgment
    carries a reason ("why"). The Rule Engine consumes these as facts only.
    """

    # Core dimensions (v1 compatible)
    task_response: DimensionInsight
    coherence: DimensionInsight
    organization: DimensionInsight
    cefr_estimate: str
    major_learning_issue: str
    available: bool

    # Extended educational dimensions (v2) — defaulted for backward compatibility
    topic_understanding: DimensionInsight = field(default_factory=_empty_insight)
    idea_development: DimensionInsight = field(default_factory=_empty_insight)
    goal_alignment: DimensionInsight = field(default_factory=_empty_insight)
    vocabulary: VocabularyInsight = field(default_factory=_empty_vocab)
    grammar_notes: tuple[GrammarNote, ...] = ()
    cefr_reason: str = ""
    progress_comparison: str = ""
    learning_diagnosis: str = ""
    revision_priority: str = ""
    encouragement: str = ""
    strengths: tuple[str, ...] = ()
    coach_guidance: CoachGuidance = field(default_factory=_empty_coach_guidance)

    analyzer_version: str = ANALYZER_FACTS_VERSION
    model_name: str = ""
    source: str = "claude"

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "task_response": self.task_response.to_dict(),
            "coherence": self.coherence.to_dict(),
            "organization": self.organization.to_dict(),
            "topic_understanding": self.topic_understanding.to_dict(),
            "idea_development": self.idea_development.to_dict(),
            "goal_alignment": self.goal_alignment.to_dict(),
            "vocabulary": self.vocabulary.to_dict(),
            "grammar_notes": [note.to_dict() for note in self.grammar_notes],
            "cefr_estimate": self.cefr_estimate,
            "cefr_reason": self.cefr_reason,
            "progress_comparison": self.progress_comparison,
            "learning_diagnosis": self.learning_diagnosis,
            "revision_priority": self.revision_priority,
            "encouragement": self.encouragement,
            "strengths": list(self.strengths),
            "coach_guidance": self.coach_guidance.to_dict(),
            "major_learning_issue": self.major_learning_issue,
            "available": self.available,
            "analyzer_version": self.analyzer_version,
            "model_name": self.model_name,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class EducationalAnalysisContext:
    """Prompt context for Claude — built by hybrid engine from rule facts + blueprint."""

    official_cefr: str
    writing_prompt: str
    chain_node_id: str
    genre: str
    task_type: str
    narrative_why: str
    grammar_primary: str
    vocabulary_primary: tuple[str, ...]
    learning_outcomes: tuple[str, ...]
    success_criteria: tuple[tuple[str, str], ...]
    rule_summary: str
    personal_goal: str = "general_english"
    goal_label: str = "General English"
    revision_number: int = 1
    previous_cefr: str = ""
    previous_task_score: float = 0.0
    previous_draft_excerpt: str = ""


def unavailable_claude_facts(*, reason: str = "analyzer_unavailable") -> ClaudeEducationalFacts:
    return ClaudeEducationalFacts(
        task_response=DimensionInsight(0.0, reason),
        coherence=DimensionInsight(0.0, ""),
        organization=DimensionInsight(0.0, ""),
        cefr_estimate="",
        major_learning_issue="",
        available=False,
        source=reason,
    )
