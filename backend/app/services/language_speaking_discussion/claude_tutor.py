"""Claude Discussion Tutor — Claude owns the entire Guided Discussion turn (E3).

Ownership contract (M12 Scene Director philosophy, discussion runtime only):
- Claude owns follow-ups, corrections, reasoning, discussion flow, and
  progression signals through the frozen Educational Case steps.
- GPT owns STT/TTS only (outside this module; discussion remains its own runtime).
- Never call Alex, LiveBridge, or Scene Practice rehearsal APIs from here.
- On Claude failure: deterministic template fallback — never another LLM.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.claude_service import generate_claude_json, is_claude_configured
from app.services.language_educational_package.types import DiscussionStep, EducationalPackage
from app.services.language_speaking_discussion.guards import guard_tutor_payload
from app.services.language_speaking_discussion.types import DiscussionPhase, DiscussionRuntimeState

logger = logging.getLogger(__name__)

TUTOR_PROVIDER_CLAUDE = "claude-discussion-tutor"
TUTOR_PROVIDER_TEMPLATE = "template_fallback"

# Backward-compatible alias for any caller still checking the old GPT label.
TUTOR_PROVIDER_GPT = TUTOR_PROVIDER_CLAUDE

OPENING_SYSTEM_PROMPT = """You are the Claude Discussion Tutor for EduSpark Guided Discussion.
Generate the FIRST spoken question that opens this frozen Educational Case discussion.
Hard rules:
- 1–3 short sentences the student will HEAR.
- Ground the question in the current frozen step prompt and story spine.
- Sound warm and natural — start the conversation, do not quiz vocabulary first.
- NEVER invent a new story world, characters, CEFR, scores, or promotion talk.
- Do not greet with empty "Hello / How are you" only — ask about THIS case.
Respond with JSON only:
{"assistant_utterance":"...","micro_correction":null,"request_advance":false}
"""


SYSTEM_PROMPT = """You are the Claude Discussion Tutor for EduSpark Guided Discussion.
You own this frozen Educational Case discussion completely: follow-up questions,
micro-corrections, reasoning, discussion flow, and when the student is ready to
advance to the next frozen step. No other system decides the tutoring turn.

Discuss THIS case as a real-life situation (understanding, reasoning, decisions,
opinions, experience, transfer) — not as a vocabulary quiz first.

Hard rules:
- Stay inside the current discussion step and THIS Educational Case only.
- NEVER invent a new story/world, new lesson content, vocabulary targets, grammar
  lessons, objectives, CEFR, scores, mastery, promotion, or readiness.
- You may briefly micro-correct (at most one issue) then continue communication.
- Keep replies short (1–3 short sentences). Sound like a warm teacher.
- Do not create an endless interview. If the student gives a meaningful answer
  of 4+ words, acknowledge it and set request_advance true instead of asking
  another follow-up on the same step.
- Progression: set request_advance true only when the student clearly answered
  the current frozen step well enough to move on. You do not invent new steps —
  the engine advances through the package ladder.

Respond with JSON only:
{"assistant_utterance":"...","micro_correction":null|{"brief":"...","corrected_form":"..."},"request_advance":false}
"""


def _discussion_subset(package: EducationalPackage, step: DiscussionStep) -> dict[str, Any]:
    material = package.input_material
    excerpts = []
    for b in material.body_blocks[:4]:
        excerpts.append({"ref": b.block_ref, "text": b.text[:240]})
    vocab = []
    for vid in step.vocabulary_ids:
        for e in package.vocabulary_in_context.entries:
            if e.vocabulary_id == vid:
                vocab.append({"id": e.vocabulary_id, "surface": e.surface, "gloss": e.brief_gloss})
    spine = package.story_spine
    return {
        "package_title": material.title,
        "material_kind": material.kind.value,
        "story_spine": {
            "title": spine.title or material.title,
            "setting": spine.setting,
            "conflict": spine.conflict,
            "decision_point": spine.decision_point,
            "continuation_hook": spine.continuation_hook,
            "discussion_hooks": list(spine.discussion_hooks[:4]),
            "characters": [c.name for c in spine.characters[:4]],
            "stakeholders": list(spine.stakeholders[:6]),
            "case_category": spine.case_category,
            "case_archetype": spine.case_archetype,
            "ending_type": spine.ending_type,
        },
        "excerpts": excerpts,
        "current_step": step.to_dict(),
        "opening_move": package.discussion.opening_move,
        "closing_move": package.discussion.closing_move,
        "vocab_in_play": vocab,
    }


def build_tutor_user_payload(
    *,
    package: EducationalPackage,
    state: DiscussionRuntimeState,
    step: DiscussionStep,
    student_response: str,
) -> str:
    recent_corrections = state.corrections_shown[-3:]
    payload = {
        "frozen_package_subset": _discussion_subset(package, step),
        "discussion_state": {
            "step_index": state.step_index,
            "step_id": step.step_id,
            "assistant_turns_used": state.assistant_turns_used,
            "max_assistant_turns": step.max_assistant_turns,
            "answered_step_ids": list(state.answered_step_ids),
        },
        "recent_corrections_shown": recent_corrections,
        "student_response": student_response,
        "forbidden": [
            "new_objectives",
            "new_vocabulary_ids",
            "cefr",
            "scores",
            "promotion",
            "grammar_lecture",
            "leave_lesson",
            "invent_new_story_world",
            "new_characters_or_setting",
            "alex",
            "scene_practice",
            "rehearsal_respond",
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def template_tutor_reply(
    *,
    step: DiscussionStep,
    student_response: str,
) -> dict[str, Any]:
    """Deterministic tutor when Claude is unavailable (tests / offline)."""
    text = (student_response or "").strip()
    correction = None
    if len(text.split()) <= 2 and text:
        correction = {
            "brief": "Try a fuller sentence.",
            "corrected_form": f"I think… ({step.prompt[:80]})",
        }
        utterance = (
            f"Thanks — say a bit more in a full sentence. "
            f"Remember the question: {step.prompt}"
        )
        advance = False
    else:
        utterance = (
            f"Nice idea. {step.prompt}" if not text else
            "Good — that answers this step. Let's continue when you're ready."
        )
        advance = bool(text) and len(text.split()) >= 4
    return guard_tutor_payload(
        {
            "assistant_utterance": utterance,
            "micro_correction": correction,
            "request_advance": advance,
        }
    )


def template_opening_reply(*, step: DiscussionStep) -> dict[str, Any]:
    """Deterministic opening when Claude is unavailable."""
    prompt = (step.prompt or "").strip() or "What happened in this situation, and what would you do?"
    return guard_tutor_payload(
        {
            "assistant_utterance": prompt,
            "micro_correction": None,
            "request_advance": False,
        }
    )


async def call_discussion_opening(
    *,
    package: EducationalPackage,
    step: DiscussionStep,
) -> tuple[dict[str, Any], str]:
    """Claude authors the first spoken discussion question. Template on failure."""
    if not is_claude_configured():
        return template_opening_reply(step=step), TUTOR_PROVIDER_TEMPLATE

    state = DiscussionRuntimeState(
        package_id=package.package_id,
        content_item_id=None,
        content_fingerprint=package.content_fingerprint or "",
        phase=DiscussionPhase.waiting_for_student,
        step_index=0,
        current_step_id=step.step_id,
        assistant_turns_used=0,
        answered_step_ids=[],
        corrections_shown=[],
    )
    user = build_tutor_user_payload(
        package=package,
        state=state,
        step=step,
        student_response="",
    )
    try:
        raw = await generate_claude_json(
            user,
            system=OPENING_SYSTEM_PROMPT,
            temperature=0.5,
            max_output_tokens=500,
        )
        if not (raw or "").strip():
            raise ValueError("empty Claude discussion opening")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("opening root not object")
        guarded = guard_tutor_payload(parsed)
        if not guarded.get("assistant_utterance"):
            raise ValueError("opening missing utterance")
        guarded["request_advance"] = False
        return guarded, TUTOR_PROVIDER_CLAUDE
    except Exception as exc:  # noqa: BLE001
        logger.warning("Discussion Claude opening failed; template fallback: %s", exc)
        return template_opening_reply(step=step), TUTOR_PROVIDER_TEMPLATE


async def call_discussion_tutor(
    *,
    package: EducationalPackage,
    state: DiscussionRuntimeState,
    step: DiscussionStep,
    student_response: str,
) -> tuple[dict[str, Any], str]:
    """Return (guarded_payload, provider_name). Claude owns tutoring; template on failure."""
    if not is_claude_configured():
        return template_tutor_reply(step=step, student_response=student_response), TUTOR_PROVIDER_TEMPLATE

    user = build_tutor_user_payload(
        package=package, state=state, step=step, student_response=student_response
    )
    try:
        raw = await generate_claude_json(
            user,
            system=SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=700,
        )
        if not (raw or "").strip():
            raise ValueError("empty Claude discussion tutor response")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("tutor root not object")
        return guard_tutor_payload(parsed), TUTOR_PROVIDER_CLAUDE
    except Exception as exc:  # noqa: BLE001
        logger.warning("Discussion Claude tutor failed; template fallback: %s", exc)
        return (
            template_tutor_reply(step=step, student_response=student_response),
            TUTOR_PROVIDER_TEMPLATE,
        )
