"""Deterministic Gap Fill (short-answer completion) scoring for the AI placement exam.

Pure, dependency-free helpers only -- no DB access, no async, independently testable. The
answer-submission endpoint (app/api/language_exam.py::answer_mcq) is the only caller; it resolves
the server-side item and calls these functions only after confirming the item's own
question_type == "gap_fill".

MVP scope: exact-match against an explicitly authored accepted_answers list, after one small fixed
normalization pass. No fuzzy/edit-distance/phonetic matching, no automatic number/date/spelling
variant handling, no LLM judging -- every accepted variant (e.g. "10" vs "ten") must be authored
explicitly in accepted_answers.
"""

from __future__ import annotations

# Curly/smart single-quote variants (e.g. from a phone keyboard) folded to the plain apostrophe so
# "don't" (typed) and "don't" (curly) compare equal. Contractions are never split or rewritten --
# only this one character class is touched.
_APOSTROPHE_VARIANTS = "’‘ʼ`´"
# Trailing sentence punctuation only -- never stripped from the middle of an answer, so times
# ("3:00"), hyphenated/compound words, slashes, and codes are left untouched.
_TRAILING_PUNCTUATION = ".,!?"


def normalize_gap_fill_text(text: str, *, case_sensitive: bool = False) -> str:
    """Deterministic MVP normalization -- the same pass is applied to the student's answer and to
    every accepted_answers entry before comparison. See module docstring for exact scope."""
    if not isinstance(text, str):
        return ""
    normalized = text
    for variant in _APOSTROPHE_VARIANTS:
        normalized = normalized.replace(variant, "'")
    if not case_sensitive:
        normalized = normalized.lower()
    normalized = " ".join(normalized.split())
    normalized = normalized.rstrip(_TRAILING_PUNCTUATION).strip()
    return normalized


def gap_fill_content_error(item: dict) -> str | None:
    """Validate a resolved gap_fill item's server-side content. Returns a short machine-readable
    field name identifying the malformed part, or None if the item is well-formed enough to score.
    Never raises -- the caller decides how to fail closed and what (safely) to log."""
    accepted = item.get("accepted_answers")
    if not isinstance(accepted, list) or not accepted or not all(isinstance(a, str) for a in accepted):
        return "accepted_answers"

    case_sensitive = item.get("case_sensitive", False)
    if not isinstance(case_sensitive, bool):
        return "case_sensitive"

    if not any(normalize_gap_fill_text(a, case_sensitive=case_sensitive) for a in accepted):
        return "accepted_answers"

    max_words = item.get("max_words")
    if not isinstance(max_words, int) or isinstance(max_words, bool) or max_words <= 0:
        return "max_words"

    return None


def score_gap_fill_answer(item: dict, answer_text: str) -> bool:
    """Deterministic exact-match scoring. Caller must have already confirmed
    gap_fill_content_error(item) is None."""
    case_sensitive = bool(item.get("case_sensitive", False))
    normalized_answer = normalize_gap_fill_text(answer_text, case_sensitive=case_sensitive)
    normalized_accepted = {
        normalize_gap_fill_text(a, case_sensitive=case_sensitive) for a in item["accepted_answers"]
    }
    return normalized_answer in normalized_accepted
