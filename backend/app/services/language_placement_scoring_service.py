from __future__ import annotations

import re

from app.models.language.enums import LanguageLevel

LEVEL_ORDER = [
    LanguageLevel.A1,
    LanguageLevel.A2,
    LanguageLevel.B1,
    LanguageLevel.B2,
    LanguageLevel.C1,
    LanguageLevel.C2,
]


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def percent_to_level(pct: float) -> LanguageLevel:
    pct = _clamp(pct)
    if pct < 20:
        return LanguageLevel.A1
    if pct < 40:
        return LanguageLevel.A2
    if pct < 60:
        return LanguageLevel.B1
    if pct < 75:
        return LanguageLevel.B2
    if pct < 90:
        return LanguageLevel.C1
    return LanguageLevel.C2


def normalize_choice_answer(resp_json: dict) -> int | None:
    # Supports {selected_index: number} and {answer: number}
    for k in ("selected_index", "answer", "selectedIndex"):
        if k in resp_json:
            try:
                return int(resp_json.get(k))
            except Exception:
                return None
    return None


def score_mcq(response_json: dict, answer_key_json: dict | None, max_points: int = 1) -> float:
    if not answer_key_json:
        return 0.0
    correct = answer_key_json.get("correct_index")
    selected = normalize_choice_answer(response_json or {})
    try:
        return float(max_points) if selected is not None and int(correct) == int(selected) else 0.0
    except Exception:
        return 0.0


def _word_count(text: str) -> int:
    tokens = re.findall(r"[A-Za-z']+", text or "")
    return len(tokens)


def score_writing(response_json: dict, min_words: int | None = None) -> tuple[float, dict]:
    text = str((response_json or {}).get("text") or (response_json or {}).get("answer") or "").strip()
    wc = _word_count(text)
    min_words = int(min_words or 0)
    # Phase 1 rule scoring (no AI):
    # - basic completion score based on word count and sentence punctuation
    punct = 1 if re.search(r"[.!?]", text) else 0
    if min_words <= 0:
        min_words = 20
    length_ratio = min(1.0, wc / max(1, min_words))
    score_percent = (length_ratio * 85.0) + (punct * 15.0)
    metrics = {"word_count": wc, "min_words": min_words, "has_sentence_punct": bool(punct)}
    return _clamp(score_percent), metrics


def score_speaking(response_json: dict, min_seconds: int | None = None) -> tuple[float, dict]:
    # Phase 1: accept recording presence; lightweight heuristics only.
    media_object_id = (response_json or {}).get("media_object_id")
    duration = (response_json or {}).get("duration_seconds")
    try:
        duration = float(duration) if duration is not None else None
    except Exception:
        duration = None
    min_seconds = int(min_seconds or 0)
    if min_seconds <= 0:
        min_seconds = 20
    has_media = media_object_id is not None
    if not has_media:
        return 0.0, {"has_media": False, "min_seconds": min_seconds}
    dur_ratio = 1.0
    if duration is not None:
        dur_ratio = min(1.0, max(0.0, duration / max(1, min_seconds)))
    score_percent = (dur_ratio * 90.0) + 10.0  # reward submission even if duration unknown
    metrics = {
        "has_media": True,
        "media_object_id": media_object_id,
        "duration_seconds": duration,
        "min_seconds": min_seconds,
    }
    return _clamp(score_percent), metrics
