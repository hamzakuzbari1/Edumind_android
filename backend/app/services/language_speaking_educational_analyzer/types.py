"""Structured educational facts from Claude — speaking analysis only, never pass/fail."""

from __future__ import annotations

from dataclasses import dataclass, field

ANALYZER_FACTS_VERSION = "7.0.0"


@dataclass(frozen=True, slots=True)
class DimensionInsight:
    score: float
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"score": round(self.score, 4), "reason": self.reason}


@dataclass(frozen=True, slots=True)
class GrammarNote:
    issue: str
    rule: str = ""
    fix: str = ""
    example: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"issue": self.issue, "rule": self.rule, "fix": self.fix, "example": self.example}


@dataclass(frozen=True, slots=True)
class VocabularyInsight:
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


def _empty_insight() -> DimensionInsight:
    return DimensionInsight(0.0, "")


def _empty_vocab() -> VocabularyInsight:
    return VocabularyInsight(0.0, "")


@dataclass(frozen=True, slots=True)
class SpeakingEducationalFacts:
    """Deep educational analysis — must not contain pass/fail or promotion fields."""

    task_response: DimensionInsight
    topic_understanding: DimensionInsight
    idea_development: DimensionInsight
    coherence: DimensionInsight
    spoken_grammar: DimensionInsight
    spoken_vocabulary: VocabularyInsight
    communicative_effectiveness: DimensionInsight
    interaction_quality: DimensionInsight
    goal_alignment: DimensionInsight
    observed_cefr_estimate: str
    cefr_reason: str
    major_learning_issue: str
    pronunciation_interpretation: str
    delivery_interpretation: str
    previous_attempt_comparison: str
    learning_diagnosis: str
    single_revision_priority: str
    encouragement: str
    strengths: tuple[str, ...]
    grammar_notes: tuple[GrammarNote, ...] = ()
    available: bool = False
    analyzer_version: str = ANALYZER_FACTS_VERSION
    model_name: str = ""
    source: str = "claude"

    def to_persistence_dict(self) -> dict[str, object]:
        return {
            "task_response": self.task_response.to_dict(),
            "topic_understanding": self.topic_understanding.to_dict(),
            "idea_development": self.idea_development.to_dict(),
            "coherence": self.coherence.to_dict(),
            "spoken_grammar": self.spoken_grammar.to_dict(),
            "spoken_vocabulary": self.spoken_vocabulary.to_dict(),
            "communicative_effectiveness": self.communicative_effectiveness.to_dict(),
            "interaction_quality": self.interaction_quality.to_dict(),
            "goal_alignment": self.goal_alignment.to_dict(),
            "observed_cefr_estimate": self.observed_cefr_estimate,
            "cefr_reason": self.cefr_reason,
            "major_learning_issue": self.major_learning_issue,
            "pronunciation_interpretation": self.pronunciation_interpretation,
            "delivery_interpretation": self.delivery_interpretation,
            "previous_attempt_comparison": self.previous_attempt_comparison,
            "learning_diagnosis": self.learning_diagnosis,
            "single_revision_priority": self.single_revision_priority,
            "encouragement": self.encouragement,
            "strengths": list(self.strengths),
            "grammar_notes": [n.to_dict() for n in self.grammar_notes],
            "available": self.available,
            "analyzer_version": self.analyzer_version,
            "model_name": self.model_name,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class SpeakingAnalysisContext:
    """Prompt context — built by evaluation runtime from task + evidence summaries."""

    task_id: str
    task_type: str
    task_instructions: str
    task_prompt: str
    success_criteria: tuple[str, ...]
    target_skill_ids: tuple[str, ...]
    official_cefr: str
    speaking_goal: str
    goal_label: str
    transcript: str
    rule_summary: str
    pronunciation_summary: str
    prosody_summary: str
    evidence_availability: str
    evidence_reliability: str
    revision_number: int = 1
    previous_attempt_summary: str = ""


def unavailable_speaking_facts(*, reason: str = "analyzer_unavailable") -> SpeakingEducationalFacts:
    return SpeakingEducationalFacts(
        task_response=_empty_insight(),
        topic_understanding=_empty_insight(),
        idea_development=_empty_insight(),
        coherence=_empty_insight(),
        spoken_grammar=_empty_insight(),
        spoken_vocabulary=_empty_vocab(),
        communicative_effectiveness=_empty_insight(),
        interaction_quality=_empty_insight(),
        goal_alignment=_empty_insight(),
        observed_cefr_estimate="",
        cefr_reason="",
        major_learning_issue="",
        pronunciation_interpretation="",
        delivery_interpretation="",
        previous_attempt_comparison="",
        learning_diagnosis="",
        single_revision_priority="",
        encouragement="",
        strengths=(),
        available=False,
        source=reason,
    )
