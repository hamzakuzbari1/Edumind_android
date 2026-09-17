"""Transcript format classification and format-aware sentence limits."""

from __future__ import annotations

import re
from enum import StrEnum

from app.services.language_cefr.types import CefrListeningProfile, SentenceLimits

# Speaker labels: "Host:", "Sara:", "HOST (FIONA):", "Dr Smith:"
# Label text must stay on one line (no embedded newlines) so "Hello.\nJohn:" is not misparsed.
_SPEAKER_LABEL = re.compile(
    r"(?:^|\n)\s*([A-Z][A-Za-z.'() ]{0,40})\s*:\s*",
    re.MULTILINE,
)


class ListeningTranscriptFormat(StrEnum):
    monologue = "monologue"
    dialogue = "dialogue"
    interview = "interview"
    discussion = "discussion"
    panel = "panel"
    lecture = "lecture"
    news = "news"


# Per-format multipliers applied to the CEFR profile sentence bounds (min scale, max scale).
# Monologue/lecture keep profile limits; multi-speaker formats allow shorter per-sentence averages.
_FORMAT_SENTENCE_SCALE: dict[ListeningTranscriptFormat, tuple[float, float]] = {
    ListeningTranscriptFormat.monologue: (1.0, 1.0),
    ListeningTranscriptFormat.lecture: (0.93, 1.04),
    ListeningTranscriptFormat.news: (0.80, 0.96),
    ListeningTranscriptFormat.dialogue: (0.53, 0.72),
    ListeningTranscriptFormat.interview: (0.52, 0.80),
    ListeningTranscriptFormat.discussion: (0.53, 0.80),
    ListeningTranscriptFormat.panel: (0.53, 0.88),
}

# Minimum average speaker-turn length (words) for multi-speaker formats by CEFR level.
_MIN_AVG_TURN_WORDS: dict[str, dict[ListeningTranscriptFormat, int]] = {
    "A1": {
        ListeningTranscriptFormat.dialogue: 4,
        ListeningTranscriptFormat.interview: 4,
        ListeningTranscriptFormat.discussion: 4,
        ListeningTranscriptFormat.panel: 4,
    },
    "A2": {
        ListeningTranscriptFormat.dialogue: 6,
        ListeningTranscriptFormat.interview: 6,
        ListeningTranscriptFormat.discussion: 6,
        ListeningTranscriptFormat.panel: 6,
    },
    "B1": {
        ListeningTranscriptFormat.dialogue: 8,
        ListeningTranscriptFormat.interview: 9,
        ListeningTranscriptFormat.discussion: 8,
        ListeningTranscriptFormat.panel: 9,
    },
    "B2": {
        ListeningTranscriptFormat.dialogue: 10,
        ListeningTranscriptFormat.interview: 11,
        ListeningTranscriptFormat.discussion: 10,
        ListeningTranscriptFormat.panel: 12,
    },
    "C1": {
        ListeningTranscriptFormat.dialogue: 12,
        ListeningTranscriptFormat.interview: 14,
        ListeningTranscriptFormat.discussion: 12,
        ListeningTranscriptFormat.panel: 14,
    },
    "C2": {
        ListeningTranscriptFormat.dialogue: 14,
        ListeningTranscriptFormat.interview: 16,
        ListeningTranscriptFormat.discussion: 14,
        ListeningTranscriptFormat.panel: 16,
    },
}

_MULTI_SPEAKER_FORMATS = frozenset(
    {
        ListeningTranscriptFormat.dialogue,
        ListeningTranscriptFormat.interview,
        ListeningTranscriptFormat.discussion,
        ListeningTranscriptFormat.panel,
    }
)


def classify_transcript_format(transcript: str) -> ListeningTranscriptFormat:
    """Heuristic transcript format classifier from spoken-text cues."""
    text = (transcript or "").strip()
    lower = text.lower()
    labels = list(_SPEAKER_LABEL.finditer(text))
    label_count = len(labels)

    if label_count >= 3 and any(k in lower for k in ("panel", "joining me", "our guests", "cross currents")):
        return ListeningTranscriptFormat.panel
    if label_count >= 2 and any(
        k in lower for k in ("interview", "speaking with", "joined by", "welcome back to")
    ):
        return ListeningTranscriptFormat.interview
    if label_count >= 3 and any(
        k in lower for k in ("roundtable", "debate", "forum", "group discussion", "panel discussion")
    ):
        return ListeningTranscriptFormat.discussion
    if label_count >= 2:
        return ListeningTranscriptFormat.dialogue
    if any(k in lower for k in ("breaking news", "this is the news", "news bulletin", "reports from")):
        return ListeningTranscriptFormat.news
    if any(
        k in lower
        for k in (
            "today's lecture",
            "in this lecture",
            "good morning class",
            "professor",
            "seminar",
            "chapter",
        )
    ):
        return ListeningTranscriptFormat.lecture
    return ListeningTranscriptFormat.monologue


def get_format_sentence_limits(
    profile: CefrListeningProfile,
    fmt: ListeningTranscriptFormat,
) -> SentenceLimits:
    """Derive acceptable sentence-length bounds from CEFR profile + transcript format."""
    base = profile.sentence_limits
    scale_min, scale_max = _FORMAT_SENTENCE_SCALE[fmt]
    if fmt in _MULTI_SPEAKER_FORMATS:
        min_words = max(4, int(base.min_words * scale_min))
    else:
        min_words = max(4, round(base.min_words * scale_min))
    max_words = max(min_words + 2, round(base.max_words * scale_max))
    return SentenceLimits(min_words=min_words, max_words=max_words)


def is_multi_speaker_format(fmt: ListeningTranscriptFormat) -> bool:
    return fmt in _MULTI_SPEAKER_FORMATS


def min_average_turn_words(profile: CefrListeningProfile, fmt: ListeningTranscriptFormat) -> int | None:
    """Minimum average speaker-turn length for multi-speaker formats; None if not applicable."""
    if fmt not in _MULTI_SPEAKER_FORMATS:
        return None
    level_map = _MIN_AVG_TURN_WORDS.get(profile.level.value, {})
    return level_map.get(fmt)


def extract_labeled_turns(transcript: str) -> list[tuple[str, str]]:
    """Split transcript into (speaker_label, turn_text) pairs."""
    text = (transcript or "").strip()
    matches = list(_SPEAKER_LABEL.finditer(text))
    if not matches:
        return []
    turns: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        label = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        turn = text[start:end].strip()
        if turn:
            turns.append((label, turn))
    return turns


def extract_speaker_turns(transcript: str) -> list[str]:
    """Split transcript into speaker turns (content after each label)."""
    text = (transcript or "").strip()
    matches = list(_SPEAKER_LABEL.finditer(text))
    if not matches:
        return [text] if text else []
    turns: list[str] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        turn = text[start:end].strip()
        if turn:
            turns.append(turn)
    return turns


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text))
