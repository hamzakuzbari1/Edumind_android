"""Speaker metadata parsing for listening TTS."""

from __future__ import annotations

import re

from app.services.language_cefr.transcript_format import extract_labeled_turns
from app.services.language_listening_tts.voice_config import voice_for_gender

_LABEL_PREFIX = re.compile(r"^([A-Za-z][A-Za-z.'\s]{0,30}?)(?:\s*\([^)]*\))?\s*$")
_FEMALE_NAME_CUES = {
    "anna",
    "fatima",
    "laila",
    "layla",
    "leila",
    "maria",
    "nadia",
    "sara",
    "sarah",
}
_MALE_NAME_CUES = {
    "ahmad",
    "ahmed",
    "ali",
    "ben",
    "hassan",
    "john",
    "khaled",
    "mohammad",
    "mohammed",
    "omar",
    "sam",
}


def _normalize_label(label: str) -> str:
    cleaned = (label or "").strip()
    match = _LABEL_PREFIX.match(cleaned)
    if match:
        return match.group(1).strip().lower()
    return cleaned.lower()


def parse_speakers_metadata(body: dict | None) -> list[dict]:
    if not isinstance(body, dict):
        return []
    raw = body.get("speakers")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        out.append(
            {
                "id": str(item.get("id") or f"speaker_{idx + 1}").strip(),
                "name": name,
                "gender": str(item.get("gender") or "").strip().lower(),
            }
        )
    return out


def _lookup_speaker(label: str, speakers: list[dict]) -> dict | None:
    norm = _normalize_label(label)
    if not norm:
        return None
    for sp in speakers:
        name = str(sp.get("name") or "").strip().lower()
        if not name:
            continue
        name_norm = _normalize_label(name)
        if norm == name_norm or norm.startswith(name_norm) or name_norm in norm:
            return sp
    return None


def _infer_gender_from_label(label: str) -> str | None:
    norm = _normalize_label(label)
    tokens = {part for part in re.split(r"[^a-z]+", norm) if part}
    if tokens & _FEMALE_NAME_CUES:
        return "female"
    if tokens & _MALE_NAME_CUES:
        return "male"
    if any(token in {"mrs", "ms", "miss", "mother", "wife", "sister", "woman", "girl"} for token in tokens):
        return "female"
    if any(token in {"mr", "father", "husband", "brother", "man", "boy"} for token in tokens):
        return "male"
    return None


def build_synthesis_segments(body: dict | None) -> list[tuple[str, str]]:
    """Return ordered (text, supertonic_voice_name) segments for the lesson."""
    from app.services.language_listening_tts.voice_config import default_voice

    if not isinstance(body, dict):
        return []

    transcript = str(body.get("audio_transcript") or "").strip()
    if not transcript:
        return []

    speakers = parse_speakers_metadata(body)
    labeled = extract_labeled_turns(transcript)

    if labeled:
        label_voices: dict[str, str] = {}
        segments: list[tuple[str, str]] = []
        for label, turn in labeled:
            key = _normalize_label(label)
            if key not in label_voices:
                meta = _lookup_speaker(label, speakers)
                label_voices[key] = voice_for_gender(meta.get("gender") if meta else _infer_gender_from_label(label))
            segments.append((turn, label_voices[key]))
        return segments

    if len(speakers) == 1:
        return [(transcript, voice_for_gender(speakers[0].get("gender")))]

    return [(transcript, default_voice())]
