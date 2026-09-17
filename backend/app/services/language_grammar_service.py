"""Optional LanguageTool grammar hints — never blocks conversation."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_tool = None
_tool_unavailable = False


def _get_tool():
    global _tool, _tool_unavailable
    if _tool_unavailable:
        return None
    if _tool is not None:
        return _tool
    try:
        import language_tool_python

        _tool = language_tool_python.LanguageTool("en-US")
        return _tool
    except Exception as exc:
        logger.info("LanguageTool unavailable (optional): %s", exc)
        _tool_unavailable = True
        return None


def correct_text(text: str) -> str:
    """Deterministic spelling/grammar polish via LanguageTool. Returns input unchanged on failure."""
    cleaned = (text or "").strip()
    if not cleaned:
        return cleaned
    tool = _get_tool()
    if tool is None:
        return cleaned
    try:
        fixed = tool.correct(cleaned)
        return (fixed or cleaned).strip()
    except Exception as exc:
        logger.warning("LanguageTool correct failed (using original): %s", exc)
        return cleaned


def analyze_grammar(text: str) -> dict:
    """Return grammar hints; empty on any failure."""
    cleaned = (text or "").strip()
    if not cleaned:
        return {"available": False, "corrected_text": "", "errors": []}

    tool = _get_tool()
    if tool is None:
        return {"available": False, "corrected_text": cleaned, "errors": []}

    try:
        matches = tool.check(cleaned)
        corrected = tool.correct(cleaned)
        errors = []
        for m in matches:
            err_len = getattr(m, "errorLength", None) or getattr(m, "error_length", 1)
            wrong = cleaned[m.offset : m.offset + err_len] if m.offset is not None else ""
            errors.append(
                {
                    "type": "grammar",
                    "message": m.message,
                    "wrong": wrong,
                    "offset": m.offset,
                    "suggestions": (m.replacements or [])[:3],
                }
            )
        return {"available": True, "corrected_text": corrected, "errors": errors}
    except Exception as exc:
        logger.warning("LanguageTool check failed (continuing without it): %s", exc)
        return {"available": False, "corrected_text": cleaned, "errors": []}
