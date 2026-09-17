"""Canonical Grammar spine enums (G0) — shared by all language_grammar_* packages.

Grammar is NOT a fifth LanguageSkill and has no official_grammar_cefr.
"""

from __future__ import annotations

from enum import StrEnum


class GrammarCEFRBand(StrEnum):
    """Intro band for a grammar topic — anchor reference only, not an official CEFR skill."""

    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class GrammarMasteryState(StrEnum):
    """Four-state mastery lifecycle (aligned with Writing GrammarState semantics)."""

    unknown = "unknown"
    learning = "learning"
    practicing = "practicing"
    mastered = "mastered"


class GrammarReinforcementSkill(StrEnum):
    """Skills that may reinforce a grammar topic inside a Grammar session."""

    reading = "reading"
    listening = "listening"
    writing = "writing"
    speaking = "speaking"
    vocabulary = "vocabulary"


class GrammarLessonStepKind(StrEnum):
    """Blueprint step kinds — ordering is owned by GrammarLessonBlueprint.steps."""

    warmup = "warmup"
    explanation = "explanation"
    practice = "practice"
    # Generic reinforcement (G0); prefer skill-specific kinds in G3.1+.
    reinforcement = "reinforcement"
    reading_reinforcement = "reading_reinforcement"
    listening_reinforcement = "listening_reinforcement"
    writing_reinforcement = "writing_reinforcement"
    speaking_reinforcement = "speaking_reinforcement"
    quick_review = "quick_review"
    exit_check = "exit_check"
    summary = "summary"
    homework = "homework"


class GrammarObservationType(StrEnum):
    """Typed grammar evidence roles emitted by skills (never mastery writes)."""

    formative = "formative"
    summative = "summative"
    transfer = "transfer"
    retention = "retention"


class GrammarEvidenceSourceSkill(StrEnum):
    """Which skill emitted the evidence observation."""

    reading = "reading"
    listening = "listening"
    writing = "writing"
    speaking = "speaking"
    vocabulary = "vocabulary"
    grammar_lesson = "grammar_lesson"


class GrammarLegacyIdKind(StrEnum):
    """Legacy identity namespaces bridged into canonical grammar_id."""

    speaking_gram = "speaking_gram"
    writing_structure = "writing_structure"
    bkt_grammar = "bkt_grammar"


class GrammarCandidatePriority(StrEnum):
    """Progression queue priority for candidate / stretch topics (G2.1 patch)."""

    primary = "primary"
    secondary = "secondary"
    optional = "optional"
    stretch = "stretch"


class GrammarReviewPriority(StrEnum):
    """Review urgency band — ordering authority for the review queue (G2.3)."""

    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class GrammarReviewReason(StrEnum):
    """Primary explainable reason a topic is scheduled / queued for review."""

    overdue = "overdue"
    due = "due"
    low_retention = "low_retention"
    low_confidence = "low_confidence"
    low_stability = "low_stability"
    stale_evidence = "stale_evidence"
    low_context_diversity = "low_context_diversity"
    catalog_priority = "catalog_priority"


class GrammarReviewMode(StrEnum):
    """Suggested review interaction mode — never a lesson plan."""

    quick_recall = "quick_recall"
    spaced_practice = "spaced_practice"
    context_transfer = "context_transfer"
    retention_check = "retention_check"
