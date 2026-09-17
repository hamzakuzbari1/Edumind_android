"""Gemini multimodal pronunciation assessment — per-word scoring, no local model/RAM.

Listens to the learner's audio (optionally against a target sentence for shadowing)
and returns an overall score plus per-word pronunciation scores. Degrades gracefully:
returns None on any failure so callers never break.
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path

from app.core.config import get_settings
from app.services.language_transcription_service import _normalize_to_wav_16k

logger = logging.getLogger(__name__)
settings = get_settings()

WEAK_WORD_THRESHOLD = 70  # words scoring below this are flagged as needing practice

_PROMPT_BASE = (
    "You are an English pronunciation coach. Listen to the learner's audio. {target}"
    "Return ONLY JSON with this shape: "
    '{{"transcript": string, "overall_score": integer 0-100, '
    '"clarity": integer 0-100, "fluency": integer 0-100, "pace": integer 0-100, '
    '"stress": integer 0-100, "intonation": integer 0-100, '
    '"words": [{{"word": string, "score": integer 0-100, "issue": short string or empty}}], '
    '"specific_issues": [up to 3 short strings], "improvement_tips": [up to 3 short strings], '
    '"note": one short coaching tip in English}}. '
    "Score each spoken word for pronunciation clarity (100 = clear and native-like); also rate the "
    "prosody: clarity (sound accuracy), fluency (smoothness), pace (not too fast/slow), stress "
    "(word/sentence stress), intonation (natural pitch). Keep 'issue' empty when the word is fine."
)


def _clamp(value, lo=0, hi=100) -> int:
    try:
        return max(lo, min(hi, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def _normalize_result(raw: dict | None) -> dict | None:
    if not isinstance(raw, dict):
        return None
    words_in = raw.get("words") if isinstance(raw.get("words"), list) else []
    words: list[dict] = []
    for w in words_in:
        if not isinstance(w, dict):
            continue
        word = str(w.get("word") or "").strip()
        if not word:
            continue
        score = _clamp(w.get("score"))
        words.append(
            {
                "word": word,
                "score": score,
                "issue": str(w.get("issue") or "").strip(),
                "weak": score < WEAK_WORD_THRESHOLD,
            }
        )
    overall = _clamp(raw.get("overall_score"))

    def _str_list(key: str) -> list[str]:
        v = raw.get(key)
        return [str(x).strip() for x in v if str(x).strip()][:3] if isinstance(v, list) else []

    return {
        "overall_score": overall,
        "transcript": str(raw.get("transcript") or "").strip(),
        "words": words,
        "weak_words": [w["word"] for w in words if w["weak"]],
        "note": str(raw.get("note") or "").strip(),
        # Phase 6 — prosody breakdown (default to the overall score when the model omits a dimension).
        "clarity": _clamp(raw.get("clarity")) or overall,
        "fluency": _clamp(raw.get("fluency")) or overall,
        "pace": _clamp(raw.get("pace")) or overall,
        "stress": _clamp(raw.get("stress")) or overall,
        "intonation": _clamp(raw.get("intonation")) or overall,
        "specific_issues": _str_list("specific_issues"),
        "improvement_tips": _str_list("improvement_tips"),
    }


async def _assess_claude(wav_bytes: bytes, expected_text: str | None) -> dict | None:
    from app.services.claude_service import generate_claude_json, is_claude_configured
    from app.services.language_transcription_service import transcribe_english_audio

    if not is_claude_configured():
        return None
    try:
        stt = await transcribe_english_audio(wav_bytes, suffix=".wav")
        transcript = (stt.text or "").strip()
    except Exception:
        return None
    if not transcript:
        return None
    target = f'The learner is trying to say: "{expected_text}". ' if expected_text else ""
    prompt = (
        f"{_PROMPT_BASE.format(target=target)}\n\n"
        f"Transcription of learner audio:\n\"\"\"\n{transcript}\n\"\"\""
    )
    raw = await generate_claude_json(
        prompt,
        temperature=0.2,
        max_output_tokens=1024 + 3072,
    )
    if not raw:
        return None
    return json.loads(raw.strip())


async def assess_pronunciation(
    data: bytes, *, suffix: str = ".webm", expected_text: str | None = None
) -> dict | None:
    """Assess pronunciation of the audio. Returns None when disabled/empty/unavailable."""
    from app.services.claude_service import is_claude_configured

    if not data or not is_claude_configured():
        return None

    tmp_path: Path | None = None
    wav_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        wav_path = _normalize_to_wav_16k(tmp_path)
        wav_bytes = wav_path.read_bytes()
        raw = await _assess_claude(wav_bytes, expected_text)
        return _normalize_result(raw)
    except Exception as exc:
        logger.warning("Pronunciation assessment failed (continuing without it): %s", exc)
        return None
    finally:
        for p in (tmp_path, wav_path):
            if p and p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass


_PROSODY_DIMS = ("overall", "clarity", "fluency", "pace", "stress", "intonation")


def compute_pron_trend(values: list[int]) -> str:
    """Trend of overall scores over time (oldest..newest): improving | stable | worsening."""
    vals = [int(v) for v in values if v is not None]
    if len(vals) < 4:
        return "stable"
    mid = len(vals) // 2
    first = sum(vals[:mid]) / mid
    second = sum(vals[mid:]) / (len(vals) - mid)
    if second - first >= 5:
        return "improving"
    if first - second >= 5:
        return "worsening"
    return "stable"


async def store_pronunciation_score(
    db, *, student_id: int, language_id: int, result: dict | None, source: str = "conversation"
) -> None:
    """Persist a normalized pronunciation result for history/trends (best-effort, no-op on empty)."""
    if not isinstance(result, dict) or not result.get("overall_score"):
        return
    from app.models.language.pronunciation import LanguagePronunciationScore

    note = result.get("note") or ""
    issues = result.get("specific_issues") or []
    feedback = (note + (" | " + "; ".join(issues) if issues else "")).strip() or None
    db.add(
        LanguagePronunciationScore(
            student_id=student_id,
            language_id=language_id,
            overall=_clamp(result.get("overall_score")),
            clarity=_clamp(result.get("clarity")),
            fluency=_clamp(result.get("fluency")),
            pace=_clamp(result.get("pace")),
            stress=_clamp(result.get("stress")),
            intonation=_clamp(result.get("intonation")),
            source=(source or "conversation")[:20],
            feedback=feedback,
        )
    )


async def get_history(db, *, student_id: int, language_id: int, limit: int = 30) -> list[dict]:
    """Recent pronunciation attempts (newest first)."""
    from sqlalchemy import desc, select

    from app.models.language.pronunciation import LanguagePronunciationScore

    rows = (
        await db.execute(
            select(LanguagePronunciationScore)
            .where(
                LanguagePronunciationScore.student_id == student_id,
                LanguagePronunciationScore.language_id == language_id,
            )
            .order_by(desc(LanguagePronunciationScore.id))
            .limit(limit)
        )
    ).scalars().all()
    return [
        {
            "overall": r.overall, "clarity": r.clarity, "fluency": r.fluency,
            "pace": r.pace, "stress": r.stress, "intonation": r.intonation,
            "source": r.source, "feedback": r.feedback, "created_at": r.created_at,
        }
        for r in rows
    ]


async def get_trends(db, *, student_id: int, language_id: int, window: int = 20) -> dict:
    """Per-dimension averages + overall trend over the last `window` attempts."""
    from sqlalchemy import desc, select

    from app.models.language.pronunciation import LanguagePronunciationScore

    rows = (
        await db.execute(
            select(LanguagePronunciationScore)
            .where(
                LanguagePronunciationScore.student_id == student_id,
                LanguagePronunciationScore.language_id == language_id,
            )
            .order_by(desc(LanguagePronunciationScore.id))
            .limit(window)
        )
    ).scalars().all()
    rows = list(reversed(rows))  # oldest..newest
    count = len(rows)
    averages = {
        dim: (round(sum(getattr(r, dim) for r in rows) / count) if count else 0)
        for dim in _PROSODY_DIMS
    }
    return {
        "count": count,
        "averages": averages,
        "trend": compute_pron_trend([r.overall for r in rows]),
    }


def word_similarity(spoken: str, target: str) -> int:
    """Rough word-overlap similarity (0-100) for shadowing — how close the repeat is."""
    def norm(t: str) -> list[str]:
        import re

        return [w for w in re.findall(r"[a-z']+", (t or "").lower())]

    a = norm(spoken)
    b = norm(target)
    if not b:
        return 0
    from collections import Counter

    ca, cb = Counter(a), Counter(b)
    overlap = sum((ca & cb).values())
    return _clamp(overlap / len(b) * 100)
