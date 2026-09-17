"""Shared validation helpers for language learning modules."""

from __future__ import annotations

import re

from fastapi import HTTPException, status

WORD_PATTERN = re.compile(r"[A-Za-z']+")


def count_words(text: str) -> int:
    return len(WORD_PATTERN.findall(text or ""))


def count_sentences(text: str) -> int:
    parts = re.split(r"[.!?]+", text or "")
    return len([p for p in parts if p.strip()])


def min_words_required_message(min_words: int) -> str:
    return f"Minimum {int(min_words)} words required."


def min_seconds_required_message(min_seconds: int) -> str:
    return f"Minimum {int(min_seconds)} seconds required."


def validate_writing_submission(
    text: str,
    *,
    min_words: int,
    min_sentences: int = 0,
) -> tuple[str, int, int]:
    """Reject short writing before scoring. Returns (normalized_text, word_count, sentence_count)."""
    normalized = (text or "").strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text required")

    min_words = max(1, int(min_words or 20))
    min_sentences = max(0, int(min_sentences or 0))
    wc = count_words(normalized)
    sc = count_sentences(normalized)

    if wc < min_words:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=min_words_required_message(min_words),
        )
    if min_sentences > 0 and sc < min_sentences:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum {min_sentences} sentences required.",
        )
    return normalized, wc, sc


def validate_speaking_duration(duration_seconds: int | None, *, min_seconds: int) -> int:
    min_seconds = max(1, int(min_seconds or 20))
    if duration_seconds is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=min_seconds_required_message(min_seconds),
        )
    duration = int(duration_seconds)
    if duration < min_seconds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=min_seconds_required_message(min_seconds),
        )
    return duration
