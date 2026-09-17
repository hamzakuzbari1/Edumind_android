"""Speaking coach orchestration: LLM call -> structured JSON -> conversation memory."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid

from app.core.config import get_settings
from app.services.ai_service import generate_llm_json
from app.services.conversation_memory import conversation_memory
from app.services.speaking_coach_prompts import (
    SYSTEM_PROMPT_EXPLAIN,
    SYSTEM_PROMPT_FULL,
    SYSTEM_PROMPT_TURN,
    build_explain_user_prompt,
    build_turn_user_prompt,
)

logger = logging.getLogger(__name__)
settings = get_settings()

_MAX_TOKENS = 8192

_TAG_RE = re.compile(r"\[(?:error|fix):\s*(.*?)\]")

_EXPLAIN_TTL = 60 * 30
_explain_cache: dict[str, tuple[float, str]] = {}


def _strip_tags(text: str) -> str:
    return _TAG_RE.sub(r"\1", text or "").strip()


def _parse_json(raw: str) -> dict | None:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _cache_explanation(turn_id: str, text: str) -> None:
    now = time.time()
    for k in [k for k, (exp, _) in _explain_cache.items() if exp < now]:
        _explain_cache.pop(k, None)
    _explain_cache[turn_id] = (now + _EXPLAIN_TTL, text)


def get_explanation(turn_id: str) -> str | None:
    entry = _explain_cache.get(turn_id)
    if not entry:
        return None
    expiry, text = entry
    if expiry < time.time():
        _explain_cache.pop(turn_id, None)
        return None
    return text


async def coach_turn(
    *, session_id: str, transcript: str, cefr_level: str, defer_explanation: bool = True
) -> dict:
    transcript = (transcript or "").strip()
    turn_id = uuid.uuid4().hex
    if not transcript:
        return {
            "turn_id": turn_id,
            "user_sentence_evaluated": "",
            "corrected_sentence": "",
            "explanation": "",
            "ai_reply": "I didn't catch that. Could you please say it again?",
            "explanation_pending": False,
        }

    history = await conversation_memory.get(session_id)
    system = SYSTEM_PROMPT_TURN if defer_explanation else SYSTEM_PROMPT_FULL
    user_prompt = build_turn_user_prompt(transcript=transcript, cefr_level=cefr_level, history=history)

    raw = await generate_llm_json(
        user_prompt, system=system, temperature=0.3, max_output_tokens=_MAX_TOKENS
    )
    data = _parse_json(raw) or {}

    result = {
        "turn_id": turn_id,
        "user_sentence_evaluated": (data.get("user_sentence_evaluated") or transcript).strip(),
        "corrected_sentence": (data.get("corrected_sentence") or transcript).strip(),
        "explanation": (data.get("explanation") or "").strip(),
        "ai_reply": (data.get("ai_reply") or "Let's keep practicing — tell me more.").strip(),
        "explanation_pending": False,
    }

    await conversation_memory.append(session_id, "user", transcript)
    await conversation_memory.append(session_id, "assistant", result["ai_reply"])

    if defer_explanation and not result["explanation"]:
        result["explanation_pending"] = True

    return result


async def generate_explanation_task(
    *, turn_id: str, original: str, corrected: str, cefr_level: str
) -> None:
    try:
        user_prompt = build_explain_user_prompt(
            original=_strip_tags(original),
            corrected=_strip_tags(corrected),
            cefr_level=cefr_level,
        )
        raw = await generate_llm_json(
            user_prompt, system=SYSTEM_PROMPT_EXPLAIN, temperature=0.3, max_output_tokens=_MAX_TOKENS
        )
        data = _parse_json(raw) or {}
        _cache_explanation(turn_id, (data.get("explanation") or "").strip())
    except Exception as exc:
        logger.warning("Speaking coach explanation failed for %s: %s", turn_id, exc)
        _cache_explanation(turn_id, "")


async def reset_session(session_id: str) -> None:
    await conversation_memory.clear(session_id)
