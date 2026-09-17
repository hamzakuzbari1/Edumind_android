"""Response Normalizer types (W5) — parse and shape raw LLM output; no educational logic."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

NORMALIZER_VERSION = "5.0.0"


class NormalizationIssueCode(StrEnum):
    """Structural normalization failure codes."""

    invalid_json = "invalid_json"
    not_object = "not_object"
    missing_required_field = "missing_required_field"
    wrong_field_type = "wrong_field_type"
    malformed_array = "malformed_array"
    unknown_top_level_keys = "unknown_top_level_keys"


@dataclass(frozen=True, slots=True)
class NormalizationIssue:
    code: NormalizationIssueCode
    field: str
    message: str


@dataclass(frozen=True, slots=True)
class WritingLlmRawResponse:
    """Raw LLM output before normalization (architecture contract — no runtime LLM in W5)."""

    raw_text: str
    llm_version: str = "mock"
    response_format: str = "json"


# Canonical field names after normalization (LLM may use aliases).
CANONICAL_LLM_OUTPUT_FIELDS: frozenset[str] = frozenset(
    {
        "mission_title",
        "writing_context",
        "instructions",
        "writing_prompt",
        "constraints",
        "checklist",
        "tips",
        "learning_outcomes",
        "success_criteria",
        "expected_output",
        "grammar_display",
        "vocabulary_display",
        "estimated_time_minutes",
    }
)

# Aliases the normalizer accepts and maps to canonical names.
LLM_FIELD_ALIASES: dict[str, str] = {
    "missionTitle": "mission_title",
    "title": "mission_title",
    "mission_context": "writing_context",
    "missionContext": "writing_context",
    "context": "writing_context",
    "writingContext": "writing_context",
    "student_context": "writing_context",
    "prompt": "writing_prompt",
    "writingPrompt": "writing_prompt",
    "instruction": "instructions",
    "instruction_list": "instructions",
    "constraint": "constraints",
    "check_list": "checklist",
    "tip": "tips",
    "learningOutcome": "learning_outcomes",
    "learning_outcome": "learning_outcomes",
    "outcomes": "learning_outcomes",
    "successCriteria": "success_criteria",
    "success_criterion": "success_criteria",
    "expectedOutput": "expected_output",
    "output_format": "expected_output",
    "grammarDisplay": "grammar_display",
    "grammar_focus": "grammar_display",
    "vocabularyDisplay": "vocabulary_display",
    "vocabulary_focus": "vocabulary_display",
    "estimatedTimeMinutes": "estimated_time_minutes",
    "total_minutes": "estimated_time_minutes",
}

ARRAY_FIELDS: frozenset[str] = frozenset(
    {
        "instructions",
        "constraints",
        "checklist",
        "tips",
        "learning_outcomes",
        "success_criteria",
    }
)

STRING_FIELDS: frozenset[str] = frozenset(
    {
        "mission_title",
        "writing_context",
        "writing_prompt",
        "expected_output",
        "grammar_display",
        "vocabulary_display",
    }
)

REQUIRED_NORMALIZED_FIELDS: frozenset[str] = frozenset(
    {
        "mission_title",
        "writing_context",
        "instructions",
        "writing_prompt",
    }
)


@dataclass(frozen=True, slots=True)
class WritingNormalizedLessonDraft:
    """Structured lesson draft after normalization — not yet validated or repaired."""

    mission_title: str
    writing_context: str
    instructions: tuple[str, ...]
    writing_prompt: str
    constraints: tuple[str, ...] = ()
    checklist: tuple[str, ...] = ()
    tips: tuple[str, ...] = ()
    learning_outcomes: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()
    expected_output: str = ""
    grammar_display: str = ""
    vocabulary_display: str = ""
    estimated_time_minutes: int | None = None
    normalizer_version: str = NORMALIZER_VERSION
    unknown_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "mission_title": self.mission_title,
            "writing_context": self.writing_context,
            "instructions": list(self.instructions),
            "writing_prompt": self.writing_prompt,
            "constraints": list(self.constraints),
            "checklist": list(self.checklist),
            "tips": list(self.tips),
            "learning_outcomes": list(self.learning_outcomes),
            "success_criteria": list(self.success_criteria),
            "expected_output": self.expected_output,
            "grammar_display": self.grammar_display,
            "vocabulary_display": self.vocabulary_display,
            "estimated_time_minutes": self.estimated_time_minutes,
        }


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """Outcome of response normalization."""

    success: bool
    draft: WritingNormalizedLessonDraft | None
    issues: tuple[NormalizationIssue, ...]
    normalizer_version: str = NORMALIZER_VERSION
