"""Speaking prompts — AI feedback pipeline (STT -> grammar -> tutor reply -> TTS -> score).

Ports the reference prototype shape (whisper STT -> llama/ollama tutor -> language_tool
grammar -> TTS) onto eduspark's existing engine wrappers. Every external step degrades
gracefully so the endpoint always returns 200, even when Whisper / the LLM / TTS are down.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.language.enums import LanguageLevel
from app.models.media import MediaObject
from app.services.ai_service import generate_ollama_text
from app.services.language_grammar_service import analyze_grammar
from app.services.language_placement_scoring_service import percent_to_level, score_speaking
from app.services.language_reply_tts_service import synthesize_english_reply
from app.services.language_transcription_service import transcribe_english_audio

logger = logging.getLogger(__name__)
settings = get_settings()

# Ported from the reference prototype tutor prompt, made CEFR-aware + prompt-aware.
TUTOR_SYSTEM_PROMPT = (
    "You are an English conversation tutor for a language learner.\n"
    "Rules:\n"
    "- If the sentence is correct -> respond naturally (do NOT repeat it back).\n"
    "- If it is wrong -> correct it briefly, then continue the conversation.\n"
    "- Keep replies short and natural.\n"
    "- Match the learner's CEFR level: use vocabulary and grammar appropriate for it.\n"
    "- Stay on the topic of the speaking prompt the learner is practising.\n"
    "- Reply in plain English only. Do not use JSON, markdown, or labels."
)


def _read_media_bytes(media: MediaObject) -> tuple[bytes, str]:
    """Read recording bytes from local disk. Returns (data, suffix); empty on failure."""
    try:
        path = Path(settings.UPLOAD_DIR) / media.storage_key
        suffix = Path(media.storage_key).suffix or ".webm"
        return path.read_bytes(), suffix
    except Exception as exc:  # missing file, permissions, non-local storage, etc.
        logger.warning("Speaking feedback: could not read media %s: %s", getattr(media, "id", None), exc)
        return b"", ".webm"


def _build_tutor_user_prompt(*, prompt_text: str, level: str, transcript: str, corrected_text: str) -> str:
    lines = [f"Learner CEFR level: {level}."]
    if prompt_text:
        lines.append(f"Speaking prompt: {prompt_text}")
    lines.append(f"Learner said: {transcript}")
    if corrected_text and corrected_text.strip() and corrected_text.strip() != transcript.strip():
        lines.append(f"Grammar-corrected version: {corrected_text}")
    lines.append("Respond as the tutor.")
    return "\n".join(lines)


async def _generate_tutor_reply(*, prompt_text: str, level: str, transcript: str, corrected_text: str) -> str:
    """Single plain-text tutor reply via the configured provider. Never raises."""
    if not transcript.strip():
        return ""

    user_prompt = _build_tutor_user_prompt(
        prompt_text=prompt_text,
        level=level,
        transcript=transcript,
        corrected_text=corrected_text,
    )

    if settings.LLM_PROVIDER.lower() == "ollama":
        try:
            reply = await generate_ollama_text(
                user_prompt,
                system=TUTOR_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=256,
            )
            return (reply or "").strip()
        except Exception as exc:
            logger.warning("Speaking feedback: Ollama tutor reply failed: %s", exc)
            return ""

    from app.services.claude_service import generate_claude_text, is_claude_configured

    if is_claude_configured():
        try:
            reply = await generate_claude_text(
                user_prompt,
                system=TUTOR_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=256 + 3072,
                timeout=60.0,
            )
            return (reply or "").strip()
        except Exception as exc:
            logger.warning("Speaking feedback: Claude tutor reply failed: %s", exc)
            return ""

    logger.info("Speaking feedback: no LLM provider configured — skipping tutor reply")
    return ""


def _word_count(text: str) -> int:
    import re

    return len(re.findall(r"[A-Za-z']+", text or ""))


async def analyze_speaking_recording(
    db: AsyncSession,
    *,
    student_id: int,
    media: MediaObject,
    prompt_text: str,
    level: LanguageLevel | None,
    duration_seconds: int | None,
    min_seconds: int,
) -> dict:
    """Run the full AI feedback pipeline for one speaking-prompt recording.

    Pipeline: read bytes -> transcribe -> grammar check -> tutor reply -> reply TTS -> score.
    Each external step is isolated so a failure never raises out of this function.
    """
    level_str = level.value if level else LanguageLevel.A1.value

    # 1) Transcribe (transcribe_english_audio already swallows its own errors).
    data, suffix = _read_media_bytes(media)
    stt = await transcribe_english_audio(data, suffix=suffix)
    transcript = (stt.text or "").strip()

    # 2) Grammar (sync, already graceful — never raises).
    grammar = analyze_grammar(transcript)
    grammar_available = bool(grammar.get("available"))
    corrected_text = grammar.get("corrected_text") or transcript
    errors = grammar.get("errors") or []

    # 3) Tutor reply via configured LLM (graceful).
    reply = await _generate_tutor_reply(
        prompt_text=prompt_text,
        level=level_str,
        transcript=transcript,
        corrected_text=corrected_text,
    )

    # 4) Optional reply audio (returns None when TTS disabled / unavailable; never raises here).
    reply_media: MediaObject | None = None
    if reply:
        try:
            reply_media = await synthesize_english_reply(db, student_id=student_id, text=reply)
        except Exception as exc:
            logger.warning("Speaking feedback: reply TTS failed: %s", exc)
            reply_media = None

    # 5) Score: duration component + grammar-accuracy component.
    duration_pct, dur_metrics = score_speaking(
        {"media_object_id": media.id, "duration_seconds": duration_seconds},
        min_seconds=min_seconds,
    )
    word_count = _word_count(transcript)
    if transcript:
        accuracy = max(0.0, 100.0 - (len(errors) / max(1, word_count)) * 150.0)
        score_percent = round(0.4 * float(duration_pct) + 0.6 * accuracy, 2)
    elif stt.engine == "disabled":
        # Whisper intentionally off (ENABLE_WHISPER=false): fall back to legacy
        # duration-only scoring so deployments without STT still work.
        accuracy = 0.0
        score_percent = round(float(duration_pct), 2)
    else:
        # STT produced no usable speech (silence, empty audio, or transcription
        # failure). Never reward mere recording length with a passing score.
        accuracy = 0.0
        score_percent = 0.0
    level_estimate = percent_to_level(score_percent)

    metrics = {
        "has_media": dur_metrics.get("has_media", True),
        "duration_seconds": dur_metrics.get("duration_seconds"),
        "min_seconds": min_seconds,
        "word_count": word_count,
        "grammar_errors": len(errors),
        "grammar_available": grammar_available,
        "accuracy_pct": round(accuracy, 2),
        "duration_pct": round(float(duration_pct), 2),
        "stt_engine": stt.engine,
        "stt_low_confidence": bool(stt.low_confidence),
        "has_reply_audio": reply_media is not None,
    }

    return {
        "transcript": transcript,
        "correction": {"corrected_text": corrected_text, "errors": errors},
        "grammar_available": grammar_available,
        "reply": reply,
        "reply_media": reply_media,
        "score_percent": score_percent,
        "level_estimate": level_estimate,
        "metrics": metrics,
    }
