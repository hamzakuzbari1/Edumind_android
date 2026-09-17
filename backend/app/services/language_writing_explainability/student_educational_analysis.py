"""Student-facing educational analysis (teacher read) — render-only from Claude facts.

Surfaces the analyzer's educational facts to the browser. It never carries pass/fail,
readiness, or promotion — those remain owned by the Rule Engine.
"""

from __future__ import annotations

from app.services.language_writing_educational_analyzer.types import ClaudeEducationalFacts

STUDENT_EDUCATIONAL_ANALYSIS_VERSION = "2.0.0"


def _provider_for(source: str) -> str:
    """Human-readable provider for the analysis source (provenance only)."""
    if source == "claude":
        return "anthropic"
    if source == "mock":
        return "heuristic"
    return source or "unknown"


def build_student_educational_analysis(facts: ClaudeEducationalFacts | None) -> dict[str, object]:
    """Map Claude educational facts into a safe student payload."""
    if facts is None or not facts.available:
        return {"available": False, "analysis_version": STUDENT_EDUCATIONAL_ANALYSIS_VERSION}

    return {
        "available": True,
        "source": facts.source,
        "provider": _provider_for(facts.source),
        "model_name": facts.model_name,
        "analyzer_version": facts.analyzer_version,
        "task_response": facts.task_response.reason,
        "topic_understanding": facts.topic_understanding.reason,
        "coherence": facts.coherence.reason,
        "organization": facts.organization.reason,
        "idea_development": facts.idea_development.reason,
        "goal_alignment": facts.goal_alignment.reason,
        "vocabulary": facts.vocabulary.reason,
        "vocabulary_range": facts.vocabulary.range_comment,
        "vocabulary_suggestions": list(facts.vocabulary.suggestions),
        "repeated_words": list(facts.vocabulary.repeated_words),
        "missing_topic_words": list(facts.vocabulary.missing_topic_words),
        "grammar_notes": [note.to_dict() for note in facts.grammar_notes],
        "cefr_estimate": facts.cefr_estimate,
        "cefr_reason": facts.cefr_reason,
        "progress_comparison": facts.progress_comparison,
        "learning_diagnosis": facts.learning_diagnosis,
        "revision_priority": facts.revision_priority,
        "encouragement": facts.encouragement,
        "strengths": list(facts.strengths),
        "analysis_version": STUDENT_EDUCATIONAL_ANALYSIS_VERSION,
    }
