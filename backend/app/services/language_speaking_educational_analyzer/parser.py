"""Parse Claude speaking educational analysis JSON."""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.language_speaking_educational_analyzer.types import (
    ANALYZER_FACTS_VERSION,
    DimensionInsight,
    GrammarNote,
    SpeakingEducationalFacts,
    VocabularyInsight,
    unavailable_speaking_facts,
)

_FORBIDDEN_KEYS = (
    "pass",
    "fail",
    "passed",
    "failed",
    "ready",
    "readiness",
    "ready_to_complete",
    "complete",
    "completed",
    "completion",
    "eligible",
    "promotion",
    "promote",
    "promoted",
    "official_cefr",
    "learning_stage",
    "mastery_update",
    "next_stage",
    "stage",
    "level_up",
)


def _clamp_score(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _insight(raw: Any) -> DimensionInsight:
    if not isinstance(raw, dict):
        return DimensionInsight(0.0, "")
    return DimensionInsight(score=_clamp_score(raw.get("score")), reason=str(raw.get("reason") or "").strip())


def _str_tuple(raw: Any, *, limit: int = 12) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    for item in raw:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return tuple(out[:limit])


def _vocabulary(raw: Any) -> VocabularyInsight:
    if not isinstance(raw, dict):
        return VocabularyInsight(0.0, "")
    return VocabularyInsight(
        score=_clamp_score(raw.get("score")),
        reason=str(raw.get("reason") or "").strip(),
        range_comment=str(raw.get("range_comment") or "").strip(),
        repeated_words=_str_tuple(raw.get("repeated_words")),
        weak_choices=_str_tuple(raw.get("weak_choices")),
        missing_topic_words=_str_tuple(raw.get("missing_topic_words")),
        suggestions=_str_tuple(raw.get("suggestions")),
    )


def _grammar_notes(raw: Any) -> tuple[GrammarNote, ...]:
    if not isinstance(raw, list):
        return ()
    notes: list[GrammarNote] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        issue = str(item.get("issue") or "").strip()
        if issue:
            notes.append(
                GrammarNote(
                    issue=issue,
                    rule=str(item.get("rule") or "").strip(),
                    fix=str(item.get("fix") or "").strip(),
                    example=str(item.get("example") or "").strip(),
                )
            )
    return tuple(notes[:8])


def _loads_relaxed(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def parse_speaking_educational_json(raw: str, *, model_name: str = "") -> SpeakingEducationalFacts:
    data = _loads_relaxed(raw)
    if not data:
        return unavailable_speaking_facts(reason="parse_failed")
    if any(k in data for k in _FORBIDDEN_KEYS):
        return unavailable_speaking_facts(reason="forbidden_decision_fields")
    return SpeakingEducationalFacts(
        task_response=_insight(data.get("task_response")),
        topic_understanding=_insight(data.get("topic_understanding")),
        idea_development=_insight(data.get("idea_development")),
        coherence=_insight(data.get("coherence")),
        spoken_grammar=_insight(data.get("spoken_grammar")),
        spoken_vocabulary=_vocabulary(data.get("spoken_vocabulary")),
        communicative_effectiveness=_insight(data.get("communicative_effectiveness")),
        interaction_quality=_insight(data.get("interaction_quality")),
        goal_alignment=_insight(data.get("goal_alignment")),
        observed_cefr_estimate=str(data.get("observed_cefr_estimate") or "").strip().upper()[:2],
        cefr_reason=str(data.get("cefr_reason") or "").strip(),
        major_learning_issue=str(data.get("major_learning_issue") or "").strip(),
        pronunciation_interpretation=str(data.get("pronunciation_interpretation") or "").strip(),
        delivery_interpretation=str(data.get("delivery_interpretation") or "").strip(),
        previous_attempt_comparison=str(data.get("previous_attempt_comparison") or "").strip(),
        learning_diagnosis=str(data.get("learning_diagnosis") or "").strip(),
        single_revision_priority=str(data.get("single_revision_priority") or "").strip(),
        encouragement=str(data.get("encouragement") or "").strip(),
        strengths=_str_tuple(data.get("strengths")),
        grammar_notes=_grammar_notes(data.get("grammar_notes")),
        available=True,
        analyzer_version=ANALYZER_FACTS_VERSION,
        model_name=model_name,
        source="claude",
    )
