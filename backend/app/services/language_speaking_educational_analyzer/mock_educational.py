"""Deterministic heuristic speaking educational facts for QA/tests."""

from __future__ import annotations

import re

from app.services.language_speaking_educational_analyzer.types import (
    ANALYZER_FACTS_VERSION,
    DimensionInsight,
    GrammarNote,
    SpeakingAnalysisContext,
    SpeakingEducationalFacts,
    VocabularyInsight,
)


def build_mock_educational_facts(context: SpeakingAnalysisContext) -> SpeakingEducationalFacts:
    text = (context.transcript or "").strip()
    words = re.findall(r"\b[\w'-]+\b", text.lower())
    wc = len(words)
    task_overlap = 0.0
    if context.task_prompt:
        task_tokens = set(re.findall(r"\b\w+\b", context.task_prompt.lower()))
        if task_tokens:
            overlap = len(set(words) & task_tokens)
            task_overlap = min(1.0, overlap / max(len(task_tokens), 1) + 0.2)
    task_score = 0.2 if wc < 3 else min(1.0, 0.35 + task_overlap * 0.5 + min(wc, 40) / 80)
    grammar_score = 0.65 if wc >= 5 else 0.35
    vocab_score = min(1.0, wc / 25) if wc else 0.0
    notes: tuple[GrammarNote, ...] = ()
    if " i are " in f" {text.lower()} ":
        notes = (GrammarNote(issue="Subject-verb agreement", fix="Use 'I am'"),)
        grammar_score = 0.4
    return SpeakingEducationalFacts(
        task_response=DimensionInsight(task_score, "Mock heuristic task relevance from transcript length and prompt overlap."),
        topic_understanding=DimensionInsight(task_score * 0.9, "Mock topic understanding proxy."),
        idea_development=DimensionInsight(min(1.0, wc / 30), "Mock idea development from response length."),
        coherence=DimensionInsight(0.6 if wc >= 8 else 0.4, "Mock coherence heuristic."),
        spoken_grammar=DimensionInsight(grammar_score, "Mock grammar heuristic from transcript."),
        spoken_vocabulary=VocabularyInsight(vocab_score, "Mock vocabulary range heuristic."),
        communicative_effectiveness=DimensionInsight(task_score * 0.85, "Mock communicative effectiveness."),
        interaction_quality=DimensionInsight(0.5, "Mock interaction quality (no interaction evidence)."),
        goal_alignment=DimensionInsight(0.55, f"Mock alignment with goal {context.goal_label}."),
        observed_cefr_estimate="B1" if task_score >= 0.6 else "A2",
        cefr_reason="Mock observed band from heuristic scores.",
        major_learning_issue="task_response" if task_score < 0.5 else "grammar",
        pronunciation_interpretation=context.pronunciation_summary[:200] if context.pronunciation_summary else "",
        delivery_interpretation=context.prosody_summary[:200] if context.prosody_summary else "",
        previous_attempt_comparison=context.previous_attempt_summary[:120] if context.previous_attempt_summary else "",
        learning_diagnosis="Mock learning diagnosis for structural verification.",
        single_revision_priority="Focus on answering the task directly." if task_score < 0.5 else "Polish grammar clarity.",
        encouragement="Keep practicing — mock encouragement.",
        strengths=("Mock strength: you produced a spoken response.",) if wc >= 3 else (),
        grammar_notes=notes,
        available=True,
        analyzer_version=ANALYZER_FACTS_VERSION,
        model_name="mock-educational-analyzer",
        source="mock",
    )
