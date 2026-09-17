"""CEFR-adaptive conversation AI — Gemini via ai_service; Ollama via generate_ollama_text."""

from __future__ import annotations

import json
import logging
import re

from app.core.config import get_settings
from app.models.language.enums import LanguageLevel
from app.services.ai_service import generate_llm_json, generate_ollama_text
from app.services.claude_service import is_claude_configured
from app.services.language_conversation_prompts import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_EXPLAIN,
    build_explain_user_prompt,
    build_user_prompt,
)

logger = logging.getLogger(__name__)
settings = get_settings()

VALID_CEFR = {lv.value for lv in LanguageLevel}


def _should_use_mock() -> bool:
    return bool(settings.LANGUAGE_CONVERSATION_MOCK_AI)


def _clamp_score(value) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0


def _normalize_cefr(value: str | None, fallback: str) -> str:
    if value and value.upper() in VALID_CEFR:
        return value.upper()
    return fallback


def _parse_llm_json(raw: str) -> dict | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _mock_turn_result(*, transcript: str, effective_level: str, grammar_hints: list[dict]) -> dict:
    has_errors = bool(grammar_hints)
    corrected = grammar_hints[0].get("suggestions", [transcript])[0] if has_errors and grammar_hints else transcript
    return {
        "correction": {
            "has_errors": has_errors,
            "original": transcript,
            "corrected": corrected if has_errors else transcript,
            "errors": [
                {
                    "type": "grammar",
                    "message": h.get("message", ""),
                    "hint_ar": "Review the sentence structure.",
                }
                for h in grammar_hints[:3]
            ],
        },
        "scores": {
            "fluency": 72,
            "grammar": 68 if has_errors else 82,
            "vocabulary": 70,
            "confidence": 75,
        },
        "estimated_cefr": effective_level,
        "reply": f"That's interesting! Can you tell me more about that?",
        "follow_up": "What happened next?",
        "topic": "daily_conversation",
        "coaching_note_ar": "Keep going — you are on the right track.",
    }


def _fallback_turn_result(*, transcript: str, effective_level: str) -> dict:
    """Graceful degradation when live Gemini is unavailable or returns invalid JSON."""
    return {
        "correction": {"has_errors": False, "original": transcript, "corrected": transcript, "errors": []},
        "scores": {"fluency": 60, "grammar": 60, "vocabulary": 60, "confidence": 60},
        "estimated_cefr": effective_level,
        "reply": "I'm having a little trouble right now. Could you tell me that again in your own words?",
        "follow_up": None,
        "topic": "conversation",
        "coaching_note_ar": "Try again — the AI assistant will be back shortly.",
    }


def _normalize_turn_payload(data: dict, *, transcript: str, effective_level: str) -> dict:
    correction = data.get("correction") or {}
    scores = data.get("scores") or {}
    errors = correction.get("errors") or []
    if not isinstance(errors, list):
        errors = []
    return {
        "correction": {
            "has_errors": bool(correction.get("has_errors")),
            "original": correction.get("original") or transcript,
            "corrected": correction.get("corrected") or transcript,
            "errors": errors,
        },
        "scores": {
            "fluency": _clamp_score(scores.get("fluency")),
            "grammar": _clamp_score(scores.get("grammar")),
            "vocabulary": _clamp_score(scores.get("vocabulary")),
            "confidence": _clamp_score(scores.get("confidence")),
        },
        "estimated_cefr": _normalize_cefr(data.get("estimated_cefr"), effective_level),
        "reply": (data.get("reply") or "").strip() or "Let's keep practicing. Can you say that again?",
        "follow_up": data.get("follow_up"),
        "topic": data.get("topic") or "conversation",
        "coaching_note_ar": data.get("coaching_note_ar") or "Keep speaking in English.",
    }


async def _generate_live_json(user_prompt: str) -> str:
    if settings.LLM_PROVIDER.lower() == "ollama":
        try:
            return await generate_ollama_text(
                user_prompt,
                system=SYSTEM_PROMPT,
                max_tokens=1024,
                json_mode=True,
            )
        except Exception as exc:
            logger.warning("Ollama conversation failed: %s", exc)
            return ""

    if is_claude_configured():
        # reasoning before the visible JSON. A budget sized only for the JSON
        # leaves it truncated -> invalid -> fallback reply. Add headroom.
        return await generate_llm_json(
            user_prompt,
            system=SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=1024 + 3072,
        )

    logger.warning("No Gemini API key configured for conversation turn")
    return ""


async def generate_conversation_turn(
    *,
    transcript: str,
    effective_level: str,
    grammar_hints: list[dict],
    history: list[dict],
    focus: str | None = None,
    memory_context: str = "",
) -> dict:
    """Structured turn analysis + reply. Uses mock only when LANGUAGE_CONVERSATION_MOCK_AI=true."""
    transcript = (transcript or "").strip()
    if not transcript:
        return _normalize_turn_payload(
            {
                "correction": {"has_errors": False, "original": "", "corrected": "", "errors": []},
                "scores": {"fluency": 0, "grammar": 0, "vocabulary": 0, "confidence": 0},
                "estimated_cefr": effective_level,
                "reply": "I didn't catch that. Could you please speak again?",
                "coaching_note_ar": "Speak more clearly and move closer to the microphone.",
            },
            transcript="",
            effective_level=effective_level,
        )

    if _should_use_mock():
        return _normalize_turn_payload(
            _mock_turn_result(transcript=transcript, effective_level=effective_level, grammar_hints=grammar_hints),
            transcript=transcript,
            effective_level=effective_level,
        )

    user_prompt = build_user_prompt(
        transcript=transcript,
        effective_level=effective_level,
        grammar_hints=grammar_hints,
        history=history,
        focus=focus,
        memory_context=memory_context,
    )

    raw = await _generate_live_json(user_prompt)
    parsed = _parse_llm_json(raw)
    if not parsed:
        logger.warning("Conversation LLM returned empty or invalid JSON (provider=%s)", settings.LLM_PROVIDER)
        return _normalize_turn_payload(
            _fallback_turn_result(transcript=transcript, effective_level=effective_level),
            transcript=transcript,
            effective_level=effective_level,
        )
    return _normalize_turn_payload(parsed, transcript=transcript, effective_level=effective_level)


async def generate_correction_explanation(*, original: str, corrected: str, effective_level: str) -> str:
    """On-demand detailed explanation of one correction (ported from the speaking coach).

    Returns a short English teaching note explaining why the sentence was corrected,
    matched to the learner's CEFR level. Degrades gracefully to "" on any failure.
    """
    original = (original or "").strip()
    corrected = (corrected or "").strip()
    if not original or not corrected:
        return ""
    try:
        raw = await generate_llm_json(
            build_explain_user_prompt(original=original, corrected=corrected, effective_level=effective_level),
            system=SYSTEM_PROMPT_EXPLAIN,
            temperature=0.3,
            max_output_tokens=2048,
        )
        data = _parse_llm_json(raw) or {}
        return (data.get("explanation") or "").strip()
    except Exception as exc:
        logger.warning("Conversation correction explanation failed: %s", exc)
        return ""
