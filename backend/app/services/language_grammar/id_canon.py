"""Canonical grammar_id helpers (G0).

One ID space for the Grammar spine. Skills must not invent parallel topic IDs after cutover.
Product-facing numbering uses display_code (G001…) — never a persistent primary key.
"""

from __future__ import annotations

import re

# Canonical grammar IDs look like: gram_present_simple
GRAMMAR_ID_PREFIX = "gram_"
_GRAMMAR_ID_RE = re.compile(r"^gram_[a-z][a-z0-9_]{1,62}$")
# Product/UI index only — not a grammar_id.
_DISPLAY_CODE_RE = re.compile(r"^G\d{3}$")


def is_canonical_grammar_id(value: str) -> bool:
    """Return True if value matches the canonical grammar_id pattern."""
    text = (value or "").strip()
    return bool(_GRAMMAR_ID_RE.match(text))


def normalize_grammar_id(value: str) -> str:
    """Normalize a candidate grammar_id (strip + lower). Does not invent IDs."""
    return (value or "").strip().lower()


def assert_canonical_grammar_id(value: str) -> str:
    """Validate and return a canonical grammar_id, or raise ValueError."""
    normalized = normalize_grammar_id(value)
    if not is_canonical_grammar_id(normalized):
        raise ValueError(f"Invalid grammar_id: {value!r}")
    return normalized


def is_grammar_display_code(value: str) -> bool:
    """Return True if value matches product display_code pattern G001…G999."""
    text = (value or "").strip().upper()
    return bool(_DISPLAY_CODE_RE.match(text))


def normalize_grammar_display_code(value: str) -> str:
    """Normalize a display_code to uppercase G00x form."""
    return (value or "").strip().upper()


def assert_grammar_display_code(value: str) -> str:
    """Validate and return a display_code, or raise ValueError."""
    normalized = normalize_grammar_display_code(value)
    if not is_grammar_display_code(normalized):
        raise ValueError(f"Invalid grammar display_code: {value!r}")
    return normalized
