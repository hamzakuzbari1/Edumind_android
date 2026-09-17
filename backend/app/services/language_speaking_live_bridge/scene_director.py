"""Claude Scene Director — Claude owns every Scene Practice conversational turn (M12).

Ownership contract:
- Claude is the ONLY conversation engine during Scene Practice. It owns the
  Educational Case, the characters, the emotions, the reasoning, the questions,
  the corrections, the next scene beat, and the dialogue flow.
- GPT-4o is never called from this module and never reasons about the scene.
- On any Claude failure the caller must degrade to the deterministic template
  partner (never to another LLM).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.claude_service import generate_claude_json, is_claude_configured

logger = logging.getLogger(__name__)

DIRECTOR_PROVIDER_CLAUDE = "claude-scene-director"
DIRECTOR_PROVIDER_TEMPLATE = "template_fallback"

DIRECTOR_DECISIONS = ("correct", "accept", "probe", "advance")

_MAX_LINE_CHARS = 600
_MAX_NOTE_CHARS = 300
_MAX_LIST_ITEMS = 6

SCENE_DIRECTOR_SYSTEM = """You are the Claude Scene Director for EduSpark's Scene Practice Room.
You own this frozen Educational Case completely: its characters, emotions, reasoning,
questions, corrections, scene beats, and dialogue flow. No other system decides anything
about this conversation.

For every student turn, work in this strict order:
1. SILENTLY evaluate the student's utterance: grammar mistakes, vocabulary mistakes,
   missing target structures, and (only when a transcription confidence signal is
   provided) a brief pronunciation note. Never invent pronunciation feedback without
   that signal.
2. Choose exactly ONE decision:
   - "correct": briefly correct the student (one issue max), then continue the scene.
   - "accept": accept the response and continue naturally.
   - "probe": ask a deeper in-character follow-up question.
   - "advance": challenge the student with the next event of the scene.
3. Write the NEXT character message, fully in character, 1-3 short sentences,
   continuing THIS case only.

Hard rules:
- Stay inside this story world, characters, conflict, and decision point.
  NEVER invent a new world, new characters, or new lesson content.
- Never open with "Hello", "How are you", "Ready to practice", or "Nice to meet you".
- No scores, no CEFR levels, no grading, no promotion talk. This is rehearsal.
- The evaluation is silent: only voice a correction when decision is "correct",
  and keep it to one brief issue before continuing in character.
- Weave target vocabulary naturally when it fits; never quiz.
Respond with JSON only:
{"evaluation":{"grammar_issues":[],"vocabulary_issues":[],"missing_targets":[],"pronunciation_note":null},
"decision":"correct|accept|probe|advance",
"micro_correction":null|{"brief":"...","corrected_form":"..."},
"coaching_note":null|"...",
"next_line":{"speaker":"...","text":"..."},
"scene_beat":{"index":0,"is_final":false}}
"""

SCENE_OPENING_SYSTEM = """You are the Claude Scene Director for EduSpark's Scene Practice Room.
Write the FIRST character message that opens this scene, fully in character, continuing
the frozen Educational Case exactly where the guided discussion left it.
Hard rules:
- 1-3 short sentences, spoken by a named character from this case.
- Continue the story from the continuation hook or decision point.
- NEVER invent a new world, new characters, or new lesson content.
- Never open with "Hello", "How are you", "Ready to practice", or "Nice to meet you".
- No scores, CEFR, grading, or promotion talk.
Respond with JSON only:
{"next_line":{"speaker":"...","text":"..."}}
"""


def _clean_str(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _clean_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out = [str(x).strip()[:_MAX_NOTE_CHARS] for x in value if str(x).strip()]
    return out[:_MAX_LIST_ITEMS]


def validate_director_payload(data: Any) -> dict[str, Any] | None:
    """Validate + sanitize a Scene Director JSON payload. None when unusable."""
    if not isinstance(data, dict):
        return None

    next_line = data.get("next_line")
    if not isinstance(next_line, dict):
        return None
    line_text = _clean_str(next_line.get("text"), _MAX_LINE_CHARS)
    if not line_text:
        return None

    decision = _clean_str(data.get("decision"), 32).lower()
    if decision not in DIRECTOR_DECISIONS:
        return None

    evaluation_raw = data.get("evaluation")
    evaluation_raw = evaluation_raw if isinstance(evaluation_raw, dict) else {}
    pron = evaluation_raw.get("pronunciation_note")
    evaluation = {
        "grammar_issues": _clean_str_list(evaluation_raw.get("grammar_issues")),
        "vocabulary_issues": _clean_str_list(evaluation_raw.get("vocabulary_issues")),
        "missing_targets": _clean_str_list(evaluation_raw.get("missing_targets")),
        "pronunciation_note": _clean_str(pron, _MAX_NOTE_CHARS) or None,
    }

    correction = None
    mc = data.get("micro_correction")
    if isinstance(mc, dict):
        brief = _clean_str(mc.get("brief"), _MAX_NOTE_CHARS)
        corrected = _clean_str(mc.get("corrected_form"), _MAX_NOTE_CHARS)
        if brief or corrected:
            correction = {"brief": brief, "corrected_form": corrected}
    # A "correct" decision without any correction content is not actionable.
    if decision == "correct" and correction is None:
        decision = "accept"

    note = data.get("coaching_note")
    coaching_note = _clean_str(note, _MAX_NOTE_CHARS) or None

    beat_raw = data.get("scene_beat")
    beat_raw = beat_raw if isinstance(beat_raw, dict) else {}
    try:
        beat_index = max(0, int(beat_raw.get("index") or 0))
    except (TypeError, ValueError):
        beat_index = 0
    scene_beat = {"index": beat_index, "is_final": bool(beat_raw.get("is_final"))}

    return {
        "evaluation": evaluation,
        "decision": decision,
        "micro_correction": correction,
        "coaching_note": coaching_note,
        "next_line": {
            "speaker": _clean_str(next_line.get("speaker"), 80),
            "text": line_text,
        },
        "scene_beat": scene_beat,
    }


def build_director_user_payload(
    *,
    context: dict[str, Any],
    recent_turns: list[dict[str, str]],
    student_transcript: str,
    stt_confidence: float | None = None,
    student_cefr: str = "",
    scene_beat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Everything Claude needs for one directed turn (context payload reused as-is)."""
    return {
        "scene_context": context,
        "recent_turns": (recent_turns or [])[-10:],
        "student_transcript": (student_transcript or "").strip()[:2000],
        "stt_confidence": stt_confidence,
        "student_cefr": (student_cefr or "").strip()[:12],
        "scene_beat": scene_beat or {"index": 0, "is_final": False},
        "decisions": {
            "correct": "briefly correct one issue, then continue the scene",
            "accept": "accept and continue naturally",
            "probe": "ask a deeper in-character follow-up question",
            "advance": "challenge the student with the next scene event",
        },
    }


async def direct_scene_turn(
    *,
    context: dict[str, Any],
    recent_turns: list[dict[str, str]],
    student_transcript: str,
    stt_confidence: float | None = None,
    student_cefr: str = "",
    scene_beat: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """One directed Scene Practice turn. None => caller uses the template fallback."""
    if not is_claude_configured():
        return None
    payload = build_director_user_payload(
        context=context,
        recent_turns=recent_turns,
        student_transcript=student_transcript,
        stt_confidence=stt_confidence,
        student_cefr=student_cefr,
        scene_beat=scene_beat,
    )
    try:
        raw = await generate_claude_json(
            json.dumps(payload, ensure_ascii=False),
            system=SCENE_DIRECTOR_SYSTEM,
            temperature=0.5,
            max_output_tokens=900,
        )
        if not (raw or "").strip():
            return None
        return validate_director_payload(json.loads(raw))
    except Exception:  # noqa: BLE001 — director failure must degrade, never crash
        logger.exception("Claude Scene Director turn failed; caller falls back to template")
        return None


async def direct_scene_opening(*, context: dict[str, Any]) -> dict[str, Any] | None:
    """Claude-authored opening character line: {"speaker": ..., "text": ...} or None."""
    if not is_claude_configured():
        return None
    try:
        raw = await generate_claude_json(
            json.dumps({"scene_context": context}, ensure_ascii=False),
            system=SCENE_OPENING_SYSTEM,
            temperature=0.6,
            max_output_tokens=300,
        )
        if not (raw or "").strip():
            return None
        data = json.loads(raw)
        next_line = data.get("next_line") if isinstance(data, dict) else None
        if not isinstance(next_line, dict):
            return None
        text = _clean_str(next_line.get("text"), _MAX_LINE_CHARS)
        if not text:
            return None
        return {"speaker": _clean_str(next_line.get("speaker"), 80), "text": text}
    except Exception:  # noqa: BLE001
        logger.exception("Claude Scene Director opening failed; caller falls back to template")
        return None
