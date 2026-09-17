"""Normalize raw LLM JSON into a package draft dict."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)

FIELD_ALIASES: dict[str, str] = {
    "input": "input_material",
    "material": "input_material",
    "vocab": "vocabulary_in_context",
    "vocabulary": "vocabulary_in_context",
    "teaching_blocks": "teaching_blocks_authored",
    "blocks": "teaching_blocks_authored",
    "discussion_flow": "discussion",
    "questions": "discussion",
    "practice": "mini_practice",
    "mini_speaking": "mini_practice",
    "educational_case": "story_spine",
    "case_spine": "story_spine",
}


@dataclass(slots=True)
class NormalizationResult:
    success: bool
    draft: dict[str, Any] | None
    errors: list[str]

    @property
    def error_count(self) -> int:
        return len(self.errors)


def _strip_fences(text: str) -> str:
    text = text.strip()
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text


def _apply_aliases(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in raw.items():
        canon = FIELD_ALIASES.get(str(key), str(key))
        if canon not in out:
            out[canon] = value
    return out


def normalize_author_response(raw_text: str) -> NormalizationResult:
    errors: list[str] = []
    if not raw_text or not str(raw_text).strip():
        return NormalizationResult(success=False, draft=None, errors=["empty_author_response"])
    try:
        parsed = json.loads(_strip_fences(str(raw_text)))
    except json.JSONDecodeError as exc:
        return NormalizationResult(
            success=False, draft=None, errors=[f"invalid_json: {exc}"]
        )
    if not isinstance(parsed, dict):
        return NormalizationResult(success=False, draft=None, errors=["root_not_object"])
    draft = _apply_aliases(parsed)
    required_top = (
        "input_material",
        "vocabulary_in_context",
        "discussion",
        "reflection",
    )
    for key in required_top:
        if key not in draft:
            errors.append(f"missing_field:{key}")
    if errors:
        return NormalizationResult(success=False, draft=draft, errors=errors)
    return NormalizationResult(success=True, draft=draft, errors=[])
