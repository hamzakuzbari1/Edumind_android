"""Explicit teaching layer — a short taught micro-lesson for each curriculum objective.

Turns the product from "drill" into "teach, then drill": before practising an objective the
learner gets a clear ENGLISH explanation, the rule, worked examples, key vocabulary, a common
mistake, and a tip. English-only (Syrian students learning English).
AI-generated (cached per objective id) with a reliable curated fallback so it always works.
"""

from __future__ import annotations

import json
import logging
import re
import time

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.services.ai_service import generate_llm_json
from app.services.claude_service import is_claude_configured
from app.services.language_conversation_prompts import level_calibration_line
from app.services.language_curriculum_service import get_level_curriculum

logger = logging.getLogger(__name__)
settings = get_settings()

_CACHE_TTL = 60 * 60 * 24
_cache: dict[str, tuple[float, dict]] = {}

_SYSTEM = (
    "You are a warm, clear English teacher for Syrian secondary-school learners. Teach ONE learning "
    "objective to a learner at the given CEFR level, in simple, classroom-appropriate ENGLISH ONLY "
    "(never Arabic). Keep it short and concrete. Return ONLY JSON with this exact shape: "
    '{"explanation": str (2-4 simple English sentences teaching the idea/grammar at the learner level), '
    '"rule_points": [str] (2-4 very short English rule statements), '
    '"examples": [str] (3-4 short worked example sentences in English), '
    '"key_vocab": [{"word": str, "meaning": str}] (3-6 useful words with a simple English meaning), '
    '"common_mistake": str (one frequent learner mistake, explained in simple English), '
    '"practice_tip": str (one short encouraging tip in English)}'
)


def _parse(raw: str) -> dict | None:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        data = json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _obj_brief(obj: dict) -> dict:
    return {
        "id": obj["id"],
        "level": obj.get("level"),
        "title": obj.get("title"),
        "feature": obj.get("feature"),
        "grammar": obj.get("grammar"),
        "vocab": obj.get("vocab"),
    }


def _curated(obj: dict) -> dict:
    """Reliable fallback built straight from the objective fields (used when AI is unavailable)."""
    grammar = obj.get("grammar") or ""
    example = obj.get("example") or ""
    return {
        "explanation": (
            f"Today's objective: {obj.get('title')}. "
            + (f"Focus on the rule: {grammar}. " if grammar else "")
            + "Read the example carefully, then try to use it yourself."
        ),
        "rule_points": [p for p in [grammar] if p],
        "examples": [example] if example else [],
        "key_vocab": [],
        "common_mistake": "",
        "practice_tip": "Practise a little every day — short, regular practice sticks better than one long session.",
    }


def _normalize(lesson: dict) -> dict:
    out = {
        "explanation": str(lesson.get("explanation") or "").strip(),
        "rule_points": [str(p).strip() for p in (lesson.get("rule_points") or []) if str(p).strip()][:5],
        "examples": [],
        "key_vocab": [],
        "common_mistake": str(lesson.get("common_mistake") or "").strip(),
        "practice_tip": str(lesson.get("practice_tip") or "").strip(),
    }
    for ex in lesson.get("examples") or []:
        # Accept plain strings or {"en": ...} objects (model variance) -> a clean English sentence.
        text = ex if isinstance(ex, str) else (ex.get("en") if isinstance(ex, dict) else "")
        if str(text or "").strip():
            out["examples"].append(str(text).strip())
    for kv in lesson.get("key_vocab") or []:
        if isinstance(kv, dict) and str(kv.get("word") or "").strip():
            meaning = kv.get("meaning") or kv.get("meaning_ar") or ""
            out["key_vocab"].append({"word": str(kv["word"]).strip(), "meaning": str(meaning).strip()})
    out["examples"] = out["examples"][:5]
    out["key_vocab"] = out["key_vocab"][:6]
    return out


async def get_micro_lesson(*, objective_id: str) -> dict:
    objective_id = (objective_id or "").strip()
    level = objective_id.split("-")[0] if "-" in objective_id else "A1"
    objectives = await get_level_curriculum(level)
    obj = next((o for o in objectives if o.get("id") == objective_id), None)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objective not found")

    cached = _cache.get(objective_id)
    if cached and cached[0] > time.time():
        return {**cached[1], "objective": _obj_brief(obj)}

    lesson = None
    if is_claude_configured():
        try:
            from app.services.language_curriculum_kb_service import get_prompt_grounding

            grounding = get_prompt_grounding(
                f"{obj.get('title')} {obj.get('grammar') or ''}", level=obj.get("level")
            )
            user = (
                (grounding + "\n\n" if grounding else "")
                + f"Level: {obj['level']}. Objective: {obj.get('title')}. "
                f"Grammar focus: {obj.get('grammar')}. Vocabulary theme: {obj.get('vocab')}. "
                f"Example: {obj.get('example')}. Teach this objective now."
                + level_calibration_line(obj.get("level"))
            )
            raw = await generate_llm_json(user, system=_SYSTEM, temperature=0.5, max_output_tokens=4096)
            parsed = _parse(raw)
            if parsed and str(parsed.get("explanation") or "").strip():
                lesson = _normalize(parsed)
        except Exception as exc:
            logger.warning("Micro-lesson AI generation failed for %s: %s", objective_id, exc)

    if not lesson:
        lesson = _normalize(_curated(obj))

    _cache[objective_id] = (time.time() + _CACHE_TTL, lesson)
    return {**lesson, "objective": _obj_brief(obj)}
