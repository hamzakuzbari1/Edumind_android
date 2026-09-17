"""Discussion policy + output guards (ELP Architecture Addendum A3)."""

from __future__ import annotations

import re
from typing import Any

# Phrases that must never appear in tutor output (authority bleed).
_FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bCEFR\b",
        r"\bA1\b|\bA2\b|\bB1\b|\bB2\b|\bC1\b|\bC2\b",
        r"promot(?:e|ion|ed)\b",
        r"\bmastery\b",
        r"\bscore[sd]?\b",
        r"\bpass(?:ed|ing)?\b.*\blevel\b",
        r"official level",
        r"readiness",
        r"as an AI\b",
        r"language model",
    )
)

MAX_ASSISTANT_CHARS = 480
MAX_CORRECTION_CHARS = 160


def sanitize_tutor_text(text: str) -> str:
    cleaned = (text or "").strip()
    for pat in _FORBIDDEN_PATTERNS:
        cleaned = pat.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    if len(cleaned) > MAX_ASSISTANT_CHARS:
        cleaned = cleaned[: MAX_ASSISTANT_CHARS - 1].rstrip() + "…"
    return cleaned


def sanitize_correction(brief: str) -> str:
    cleaned = sanitize_tutor_text(brief)
    if len(cleaned) > MAX_CORRECTION_CHARS:
        cleaned = cleaned[: MAX_CORRECTION_CHARS - 1].rstrip() + "…"
    return cleaned


def guard_tutor_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize/clip Claude tutor structured output; never invent educational targets."""
    utterance = sanitize_tutor_text(str(raw.get("assistant_utterance") or raw.get("reply") or ""))
    correction = raw.get("micro_correction")
    corr_out: dict[str, str] | None = None
    if isinstance(correction, dict):
        brief = sanitize_correction(
            str(correction.get("brief") or correction.get("explanation") or "")
        )
        form = sanitize_correction(
            str(correction.get("corrected_form") or correction.get("form") or "")
        )
        if brief or form:
            corr_out = {"brief": brief, "corrected_form": form}
    request_advance = bool(raw.get("request_advance"))
    return {
        "assistant_utterance": utterance,
        "micro_correction": corr_out,
        "request_advance": request_advance,
    }
