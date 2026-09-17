"""Response Normalizer (W5) — parse raw LLM output; no educational logic."""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.language_writing.enums import ExpectedWritingOutput, OfficialWritingCEFR
from app.services.language_writing_generation.normalizer_types import (
    ARRAY_FIELDS,
    CANONICAL_LLM_OUTPUT_FIELDS,
    LLM_FIELD_ALIASES,
    NORMALIZER_VERSION,
    REQUIRED_NORMALIZED_FIELDS,
    STRING_FIELDS,
    NormalizationIssue,
    NormalizationIssueCode,
    NormalizationResult,
    WritingLlmRawResponse,
    WritingNormalizedLessonDraft,
)

_ENUM_NORMALIZERS: dict[str, type[ExpectedWritingOutput | OfficialWritingCEFR]] = {
    "expected_output": ExpectedWritingOutput,
    "official_cefr": OfficialWritingCEFR,
}


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _coerce_string(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    return None


def _coerce_string_array(value: Any) -> tuple[str, ...] | None:
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            coerced = _coerce_string(item)
            if coerced is None:
                return None
            if coerced:
                items.append(coerced)
        return tuple(items)
    return None


def _normalize_enum_value(field: str, value: str) -> str:
    enum_cls = _ENUM_NORMALIZERS.get(field)
    if enum_cls is None:
        return value
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    for member in enum_cls:
        if member.value.lower() == normalized or member.name.lower() == normalized:
            return member.value
    return value.strip()


def _rename_fields(raw: dict[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    renamed: dict[str, Any] = {}
    unknown: list[str] = []
    for key, value in raw.items():
        canonical = LLM_FIELD_ALIASES.get(key, key)
        if canonical in CANONICAL_LLM_OUTPUT_FIELDS:
            renamed[canonical] = value
        else:
            unknown.append(key)
    return renamed, tuple(unknown)


def normalize_llm_response(raw: WritingLlmRawResponse) -> NormalizationResult:
    """Parse and normalize raw LLM JSON — structural only; no blueprint access."""
    issues: list[NormalizationIssue] = []

    text = _strip_code_fence(raw.raw_text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return NormalizationResult(
            success=False,
            draft=None,
            issues=(
                NormalizationIssue(
                    code=NormalizationIssueCode.invalid_json,
                    field="raw_text",
                    message=str(exc),
                ),
            ),
        )

    if not isinstance(parsed, dict):
        return NormalizationResult(
            success=False,
            draft=None,
            issues=(
                NormalizationIssue(
                    code=NormalizationIssueCode.not_object,
                    field="root",
                    message="LLM output must be a JSON object",
                ),
            ),
        )

    renamed, unknown_fields = _rename_fields(parsed)
    if unknown_fields:
        issues.append(
            NormalizationIssue(
                code=NormalizationIssueCode.unknown_top_level_keys,
                field="root",
                message=f"Unknown keys ignored: {', '.join(unknown_fields)}",
            )
        )

    normalized: dict[str, Any] = {}
    for field in CANONICAL_LLM_OUTPUT_FIELDS:
        if field not in renamed:
            continue
        value = renamed[field]
        if field in ARRAY_FIELDS:
            coerced = _coerce_string_array(value)
            if coerced is None:
                issues.append(
                    NormalizationIssue(
                        code=NormalizationIssueCode.malformed_array,
                        field=field,
                        message=f"Expected string array for {field}",
                    )
                )
                continue
            normalized[field] = coerced
        elif field == "estimated_time_minutes":
            if isinstance(value, int):
                normalized[field] = value
            elif isinstance(value, str) and value.isdigit():
                normalized[field] = int(value)
            else:
                issues.append(
                    NormalizationIssue(
                        code=NormalizationIssueCode.wrong_field_type,
                        field=field,
                        message="Expected integer for estimated_time_minutes",
                    )
                )
        elif field in STRING_FIELDS:
            coerced = _coerce_string(value)
            if coerced is None:
                issues.append(
                    NormalizationIssue(
                        code=NormalizationIssueCode.wrong_field_type,
                        field=field,
                        message=f"Expected string for {field}",
                    )
                )
                continue
            if field == "expected_output":
                normalized[field] = _normalize_enum_value(field, coerced)
            else:
                normalized[field] = coerced

    for required in REQUIRED_NORMALIZED_FIELDS:
        if required not in normalized or not normalized[required]:
            issues.append(
                NormalizationIssue(
                    code=NormalizationIssueCode.missing_required_field,
                    field=required,
                    message=f"Required field missing or empty: {required}",
                )
            )

    blocking = [i for i in issues if i.code != NormalizationIssueCode.unknown_top_level_keys]
    if blocking:
        return NormalizationResult(success=False, draft=None, issues=tuple(issues))

    draft = WritingNormalizedLessonDraft(
        mission_title=normalized["mission_title"],
        writing_context=normalized["writing_context"],
        instructions=normalized["instructions"],
        writing_prompt=normalized["writing_prompt"],
        constraints=normalized.get("constraints", ()),
        checklist=normalized.get("checklist", ()),
        tips=normalized.get("tips", ()),
        learning_outcomes=normalized.get("learning_outcomes", ()),
        success_criteria=normalized.get("success_criteria", ()),
        expected_output=normalized.get("expected_output", ""),
        grammar_display=normalized.get("grammar_display", ""),
        vocabulary_display=normalized.get("vocabulary_display", ""),
        estimated_time_minutes=normalized.get("estimated_time_minutes"),
        unknown_fields=unknown_fields,
    )
    return NormalizationResult(success=True, draft=draft, issues=tuple(issues))
