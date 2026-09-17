"""Parse Claude educational analysis JSON into structured teacher facts."""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.language_writing_educational_analyzer.types import (
    ANALYZER_FACTS_VERSION,
    ClaudeEducationalFacts,
    CoachGuidance,
    DimensionInsight,
    GrammarNote,
    VocabularyInsight,
    unavailable_claude_facts,
)

_FORBIDDEN_KEYS = (
    "passed",
    "failed",
    "ready",
    "ready_to_complete",
    "completed",
    "eligible",
    "promotion",
    "promoted",
    "stage",
    "level_up",
)


def _clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


def _insight(raw: Any) -> DimensionInsight:
    if not isinstance(raw, dict):
        return DimensionInsight(0.0, "")
    return DimensionInsight(
        score=_clamp_score(raw.get("score")),
        reason=str(raw.get("reason") or "").strip(),
    )


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


def _grammar_notes(raw: Any, *, limit: int = 8) -> tuple[GrammarNote, ...]:
    if not isinstance(raw, list):
        return ()
    notes: list[GrammarNote] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        issue = str(item.get("issue") or "").strip()
        if not issue:
            continue
        notes.append(
            GrammarNote(
                issue=issue,
                rule=str(item.get("rule") or "").strip(),
                fix=str(item.get("fix") or "").strip(),
                example=str(item.get("example") or "").strip(),
            )
        )
    return tuple(notes[:limit])


_FORBIDDEN_GUIDANCE_TOKENS = (
    "pass",
    "fail",
    "ready to complete",
    "promotion",
    "promoted",
    "advance a stage",
    "level up",
    "official cefr",
    "readiness score",
)


def _coach_guidance(raw: Any) -> CoachGuidance:
    """Parse and validate Claude's coach guidance.

    Educational only. Returns an unavailable guidance if any required field is
    missing/duplicated or if a forbidden progression decision leaks in — the
    canonical priority selector then falls back deterministically (never to the
    first grammar error).
    """
    if not isinstance(raw, dict):
        return CoachGuidance()

    main_issue = str(raw.get("main_issue") or "").strip()
    why = str(raw.get("why_this_is_the_priority") or "").strip()
    mission = str(raw.get("revision_mission") or "").strip()
    explanation = str(raw.get("student_friendly_explanation") or "").strip()
    before = str(raw.get("before_example") or "").strip()
    after = str(raw.get("after_example") or "").strip()
    encouragement = str(raw.get("encouragement") or "").strip()

    # Required: a single issue and a mission that repairs it.
    if not main_issue or not mission:
        return CoachGuidance()

    # No progression decisions may leak into coaching text.
    blob = " ".join((main_issue, why, mission, explanation, encouragement)).lower()
    if any(tok in blob for tok in _FORBIDDEN_GUIDANCE_TOKENS):
        return CoachGuidance()

    # Fields must be distinct — a coach that repeats one sentence is not coaching.
    if main_issue.lower() == mission.lower():
        return CoachGuidance()
    if before and after and before.lower() == after.lower():
        return CoachGuidance()

    return CoachGuidance(
        main_issue=main_issue,
        why_this_is_the_priority=why,
        revision_mission=mission,
        student_friendly_explanation=explanation,
        before_example=before,
        after_example=after,
        encouragement=encouragement,
        available=True,
    )


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


# Flat arrays-of-strings in the schema — the fields where the model sometimes
# injects inline annotations (e.g. "football" - generic) that break strict JSON.
_STRING_ARRAY_FIELDS = (
    "repeated_words",
    "weak_choices",
    "missing_topic_words",
    "suggestions",
    "strengths",
)


def _sanitize_string_arrays(text: str) -> str:
    """Rebuild known string-array fields from their valid quoted literals only.

    This discards any inline annotation, comment, or bare (unquoted) junk the model
    may add inside these flat arrays, without touching object arrays like grammar_notes.
    """
    field_group = "|".join(_STRING_ARRAY_FIELDS)
    pattern = re.compile(rf'"({field_group})"\s*:\s*\[([^\]]*)\]')

    def _repl(m: "re.Match[str]") -> str:
        field = m.group(1)
        items = re.findall(r'"(?:[^"\\]|\\.)*"', m.group(2))
        return f'"{field}": [{", ".join(items)}]'

    return pattern.sub(_repl, text)


def _loads_relaxed(text: str) -> Any:
    """Parse JSON, with a conservative repair pass for common model deviations.

    Handles otherwise-silent failures without corrupting valid JSON: inline
    annotations inside flat string arrays and trailing commas. Returns None if it
    still cannot be parsed.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]

    text = _sanitize_string_arrays(text)
    # Remove trailing commas before a closing brace/bracket.
    text = re.sub(r",(\s*[}\]])", r"\1", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def parse_claude_educational_json(raw: str, *, model_name: str = "") -> ClaudeEducationalFacts:
    """Parse Claude JSON into educational facts — rejects pass/fail shaped payloads."""
    if not raw or not raw.strip():
        return unavailable_claude_facts(reason="empty_response")
    data = _loads_relaxed(_strip_fences(raw))
    if data is None:
        return unavailable_claude_facts(reason="invalid_json")
    if not isinstance(data, dict):
        return unavailable_claude_facts(reason="invalid_shape")
    if any(k in data for k in _FORBIDDEN_KEYS):
        return unavailable_claude_facts(reason="forbidden_pass_fail_fields")

    return ClaudeEducationalFacts(
        task_response=_insight(data.get("task_response")),
        coherence=_insight(data.get("coherence")),
        organization=_insight(data.get("organization")),
        topic_understanding=_insight(data.get("topic_understanding")),
        idea_development=_insight(data.get("idea_development")),
        goal_alignment=_insight(data.get("goal_alignment")),
        vocabulary=_vocabulary(data.get("vocabulary")),
        grammar_notes=_grammar_notes(data.get("grammar_notes")),
        cefr_estimate=str(data.get("cefr_estimate") or "").strip().upper(),
        cefr_reason=str(data.get("cefr_reason") or "").strip(),
        progress_comparison=str(data.get("progress_comparison") or "").strip(),
        learning_diagnosis=str(data.get("learning_diagnosis") or "").strip(),
        revision_priority=str(data.get("revision_priority") or "").strip(),
        encouragement=str(data.get("encouragement") or "").strip(),
        strengths=_str_tuple(data.get("strengths"), limit=6),
        coach_guidance=_coach_guidance(data.get("coach_guidance")),
        major_learning_issue=str(data.get("major_learning_issue") or "").strip(),
        available=True,
        analyzer_version=ANALYZER_FACTS_VERSION,
        model_name=model_name,
        source="claude",
    )
