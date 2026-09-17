"""Deterministic rotation for listening quality directives (Phase 2.1)."""

from __future__ import annotations

import hashlib
import secrets

from app.services.language_cefr.engine import normalize_cefr_level
from app.services.language_listening_quality.catalog import (
    FORMAT_BY_SITUATION,
    LISTENING_QUESTION_EMPHASIS_BY_LEVEL,
    NARRATIVE_ARCS,
    OPENING_STYLES,
    OVERUSED_TOPIC_HINTS,
    PACE_HINTS,
    SITUATION_BRIEFS,
    SITUATIONS_BY_LEVEL,
    SPEAKER_COUNT_BY_FORMAT,
)
from app.services.language_listening_quality.types import (
    EndingStyle,
    ListeningQualitySpec,
    ListeningSituationKind,
    NarrativeArc,
    OpeningStyle,
    PaceHint,
    TranscriptFormatHint,
)

_ENDING_STYLES: tuple[EndingStyle, ...] = tuple(EndingStyle)


def _rotation_digest(*parts: str) -> bytes:
    payload = "|".join(parts).encode("utf-8")
    return hashlib.sha256(payload).digest()


def _pick(digest: bytes, index: int, options: tuple) -> object:
    if not options:
        raise ValueError("Cannot pick from empty options")
    byte_val = digest[index % len(digest)]
    return options[byte_val % len(options)]


def _deprioritize_situations(
    pool: tuple[ListeningSituationKind, ...],
    themes: str,
    topics: str,
) -> tuple[ListeningSituationKind, ...]:
    blob = f"{themes} {topics}".lower()
    overused_situations = {
        ListeningSituationKind.school,
    }
    if any(hint in blob for hint in ("routine", "family", "daily")):
        filtered = tuple(s for s in pool if s not in overused_situations)
        return filtered or pool
    return pool


def build_listening_quality_spec(
    level: str,
    *,
    themes: str = "",
    topics: str = "",
    seed: str | None = None,
) -> ListeningQualitySpec:
    """Build one rotated quality spec; seed enables reproducible verification runs."""
    norm_level = normalize_cefr_level(level)
    rotation_seed = seed or secrets.token_hex(8)
    digest = _rotation_digest(norm_level, themes, topics, rotation_seed)

    pool = SITUATIONS_BY_LEVEL.get(norm_level, SITUATIONS_BY_LEVEL["B1"])
    pool = _deprioritize_situations(pool, themes, topics)
    situation: ListeningSituationKind = _pick(digest, 0, pool)  # type: ignore[assignment]

    format_pool = FORMAT_BY_SITUATION.get(situation, (TranscriptFormatHint.monologue,))
    format_hint: TranscriptFormatHint = _pick(digest, 1, format_pool)  # type: ignore[assignment]

    speaker_pool = SPEAKER_COUNT_BY_FORMAT.get(format_hint, (1,))
    speaker_count: int = _pick(digest, 2, speaker_pool)  # type: ignore[assignment]

    narrative_arc: NarrativeArc = _pick(digest, 3, NARRATIVE_ARCS)  # type: ignore[assignment]
    opening_style: OpeningStyle = _pick(digest, 4, OPENING_STYLES)  # type: ignore[assignment]
    ending_style: EndingStyle = _pick(digest, 5, _ENDING_STYLES)  # type: ignore[assignment]
    pace: PaceHint = _pick(digest, 6, PACE_HINTS)  # type: ignore[assignment]

    question_emphasis = LISTENING_QUESTION_EMPHASIS_BY_LEVEL.get(
        norm_level,
        LISTENING_QUESTION_EMPHASIS_BY_LEVEL["B1"],
    )

    return ListeningQualitySpec(
        level=norm_level,
        situation=situation,
        situation_brief=SITUATION_BRIEFS[situation],
        format_hint=format_hint,
        speaker_count=speaker_count,
        narrative_arc=narrative_arc,
        opening_style=opening_style,
        ending_style=ending_style,
        pace=pace,
        avoid_topics=OVERUSED_TOPIC_HINTS,
        listening_question_emphasis=question_emphasis,
    )
