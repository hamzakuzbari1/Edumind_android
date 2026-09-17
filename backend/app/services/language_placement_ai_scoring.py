"""Rigorous, evidence-based CEFR evaluation for placement writing & speaking.

"Smart" means: the model returns per-criterion CEFR sub-scores, integrity flags, and
evidence — and WE compute the final score deterministically as a weighted aggregate with
anti-gaming caps. We never trust a single self-reported number. Both functions return None
on any failure (no key / quota / parse) so the caller falls back to the length/duration
heuristic and placement never breaks.

Final score bands align with percent_to_level():
  A1 <20 | A2 20-39 | B1 40-59 | B2 60-74 | C1 75-89 | C2 90-100
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import tempfile
from pathlib import Path

from app.core.config import get_settings
from app.services.ai_service import generate_llm_json
from app.services.language_transcription_service import _normalize_to_wav_16k

logger = logging.getLogger(__name__)
settings = get_settings()

_MAX_TOKENS = 8192

_BANDS = (
    "CEFR sub-score bands (apply to EVERY criterion): A1=0-19, A2=20-39, B1=40-59, "
    "B2=60-74, C1=75-89, C2=90-100. Be a strict, fair examiner. Do not inflate. "
    "Judge only what the learner actually produced."
)

# Criterion weights (sum to 1.0). The final headline score is the weighted aggregate.
WRITING_WEIGHTS = {
    "task_achievement": 0.20,
    "coherence_cohesion": 0.15,
    "grammar_accuracy": 0.20,
    "grammar_range": 0.15,
    "lexical_resource": 0.20,
    "mechanics": 0.10,  # spelling, punctuation, word-spacing
}
SPEAKING_WEIGHTS = {
    "task_relevance": 0.15,
    "fluency_coherence": 0.25,
    "pronunciation": 0.20,
    "grammar_accuracy": 0.20,
    "grammar_range": 0.10,
    "lexical_resource": 0.10,
}

WRITING_SYSTEM = (
    "You are a senior CEFR writing examiner. Evaluate the learner's writing against official "
    "CEFR descriptors, criterion by criterion. "
    f"{_BANDS} "
    "Return ONLY JSON: {"
    '"criteria": {"task_achievement": int, "coherence_cohesion": int, "grammar_accuracy": int, '
    '"grammar_range": int, "lexical_resource": int, "mechanics": int}, '
    '"flags": {"off_topic": bool, "gibberish": bool, "non_english": bool, "too_short": bool, "likely_memorized": bool}, '
    '"estimated_cefr": string, "strength": string, "key_error": string, "feedback": string}'
)

SPEAKING_SYSTEM = (
    "You are a senior CEFR speaking examiner. Listen to the learner's audio and evaluate it "
    "against official CEFR descriptors, criterion by criterion. "
    f"{_BANDS} "
    "Return ONLY JSON: {"
    '"transcript": string, '
    '"criteria": {"task_relevance": int, "fluency_coherence": int, "pronunciation": int, '
    '"grammar_accuracy": int, "grammar_range": int, "lexical_resource": int}, '
    '"flags": {"off_topic": bool, "gibberish": bool, "non_english": bool, "too_short": bool, "no_speech": bool, "likely_memorized": bool}, '
    '"estimated_cefr": string, "strength": string, "key_error": string, "feedback": string}'
)


def _parse(raw: str) -> dict | None:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        return json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return None


def _clamp_int(v, lo=0, hi=100) -> int:
    try:
        return max(lo, min(hi, int(round(float(v)))))
    except (TypeError, ValueError):
        return 0


def _aggregate(criteria: dict, weights: dict, flags: dict) -> tuple[float, dict]:
    """Deterministic weighted score + anti-gaming caps. Returns (score, normalized_criteria)."""
    norm = {k: _clamp_int(criteria.get(k)) for k in weights}
    score = sum(norm[k] * w for k, w in weights.items())

    # Integrity caps — these protect against scoring nonsense as advanced.
    if flags.get("non_english") or flags.get("gibberish") or flags.get("no_speech"):
        score = min(score, 10.0)         # not assessable -> A1 floor
    elif flags.get("off_topic"):
        score = min(score, 45.0)         # off-topic cannot demonstrate full ability
    elif flags.get("too_short"):
        score = min(score, 55.0)         # too little evidence to claim B2+
    if flags.get("likely_memorized"):
        score *= 0.75                     # memorized text is weak evidence of ability

    return max(0.0, min(100.0, round(score, 2))), norm


def _flags(data: dict) -> dict:
    raw = data.get("flags") or {}
    return {k: bool(v) for k, v in raw.items()} if isinstance(raw, dict) else {}


async def score_writing_ai(*, text: str, prompt: str = "") -> tuple[float, dict] | None:
    from app.services.claude_service import is_claude_configured

    text = (text or "").strip()
    if not is_claude_configured() or not text:
        return None
    user_prompt = f'Task prompt: {prompt or "(general writing task)"}\n\nLearner\'s writing:\n"""\n{text}\n"""'
    try:
        raw = await generate_llm_json(
            user_prompt, system=WRITING_SYSTEM, temperature=0.1, max_output_tokens=_MAX_TOKENS
        )
    except Exception as exc:
        logger.warning("Placement writing AI scoring failed error_type=%s", type(exc).__name__)
        return None
    data = _parse(raw)
    if not data or "criteria" not in data:
        return None
    flags = _flags(data)
    score, criteria = _aggregate(data.get("criteria") or {}, WRITING_WEIGHTS, flags)
    metrics = {
        "scorer": "ai_rubric_v2",
        "criteria": criteria,
        "weights": WRITING_WEIGHTS,
        "flags": flags,
        "estimated_cefr": data.get("estimated_cefr"),
        "strength": (data.get("strength") or "").strip(),
        "key_error": (data.get("key_error") or "").strip(),
        "feedback": (data.get("feedback") or "").strip(),
        "word_count": len(re.findall(r"[A-Za-z']+", text)),
    }
    return score, metrics


async def _speaking_eval_claude(wav_bytes: bytes, prompt: str) -> dict | None:
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
    user = (
        f'Speaking task prompt: {prompt or "(open speaking task)"}. '
        f'Evaluate the learner audio from this transcript:\n"""\n{transcript}\n"""'
    )
    raw = await generate_claude_json(
        user,
        system=SPEAKING_SYSTEM,
        temperature=0.1,
        max_output_tokens=_MAX_TOKENS,
    )
    return _parse(raw)


async def score_speaking_ai(*, audio_data: bytes, suffix: str = ".webm", prompt: str = "") -> tuple[float, dict] | None:
    from app.services.claude_service import is_claude_configured

    if not is_claude_configured() or not audio_data:
        return None
    tmp_path: Path | None = None
    wav_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_data)
            tmp_path = Path(tmp.name)
        wav_path = _normalize_to_wav_16k(tmp_path)
        data = await _speaking_eval_claude(wav_path.read_bytes(), prompt)
    except Exception as exc:
        logger.warning("Placement speaking AI scoring failed error_type=%s", type(exc).__name__)
        return None
    finally:
        for p in (tmp_path, wav_path):
            if p and p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
    if not data or "criteria" not in data:
        return None
    flags = _flags(data)
    score, criteria = _aggregate(data.get("criteria") or {}, SPEAKING_WEIGHTS, flags)
    metrics = {
        "scorer": "ai_rubric_v2",
        "transcript": (data.get("transcript") or "").strip(),
        "criteria": criteria,
        "weights": SPEAKING_WEIGHTS,
        "flags": flags,
        "estimated_cefr": data.get("estimated_cefr"),
        "strength": (data.get("strength") or "").strip(),
        "key_error": (data.get("key_error") or "").strip(),
        "feedback": (data.get("feedback") or "").strip(),
        "has_media": True,
    }
    return score, metrics
