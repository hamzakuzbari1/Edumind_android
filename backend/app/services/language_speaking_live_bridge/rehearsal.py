"""Scene Practice rehearsal — Claude Scene Director owns dialogue; GPT is TTS/STT only."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.services.language_educational_package.types import EducationalPackage
from app.services.language_speaking_live_bridge.continuity import extract_case_continuity_fields
from app.services.language_speaking_live_bridge.scenario import gpt_rehearsal_roles_for_scenario
from app.services.language_speaking_live_bridge.scene_director import (
    DIRECTOR_PROVIDER_CLAUDE,
    direct_scene_turn,
)
from app.services.language_speaking_live_bridge.types import RehearsalState, SpeakingScenario

logger = logging.getLogger(__name__)

REHEARSAL_PROVIDER_CLAUDE = DIRECTOR_PROVIDER_CLAUDE
REHEARSAL_PROVIDER_TEMPLATE = "template_fallback"


def _rehearsal_id(package_id: str) -> str:
    digest = hashlib.sha256(f"reh:{package_id}".encode("utf-8")).hexdigest()[:12]
    return f"reh_{digest}"


def build_rehearsal_context_payload(
    *,
    package: EducationalPackage,
    scenario: SpeakingScenario,
    discussion_summary: str = "",
    weak_skills: list[str] | tuple[str, ...] | None = None,
    student_memory: dict[str, Any] | None = None,
    knowledge_highlights: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    fields = extract_case_continuity_fields(package)
    roles = gpt_rehearsal_roles_for_scenario(scenario)
    return {
        "mode": "scene_practice_claude",
        "not_hume": True,
        "grading": False,
        "educational_package": {
            "package_id": package.package_id,
            "title": fields["story_title"],
            "story_spine": {
                "setting": fields["story_world"],
                "conflict": fields["conflict"],
                "decision_point": fields["decision_point"],
                "continuation_hook": fields["continuation_hook"],
                "characters": list(fields["characters"]),
                "stakeholders": list(fields.get("stakeholders") or []),
                "case_category": fields["case_category"],
                "case_archetype": fields["case_archetype"],
            },
            "vocabulary_focus": list(scenario.vocabulary_focus),
            "grammar_focus": list(scenario.grammar_focus),
            "objectives": list(scenario.objectives),
        },
        "speaking_scenario": scenario.to_dict(),
        "gpt_roles": roles,
        "current_speaking_goal": scenario.continuation_hook or scenario.decision_point,
        "previous_discussion_summary": (discussion_summary or "")[:800],
        "weak_skills": [str(w) for w in (weak_skills or []) if str(w).strip()][:6],
        "student_memory": student_memory or {},
        "knowledge_highlights": [
            str(k) for k in (knowledge_highlights or []) if str(k).strip()
        ][:6],
        "forbidden": [
            "invent_new_story_world",
            "new_characters_outside_case",
            "scores",
            "cefr_assignment",
            "promotion",
            "formal_grading",
        ],
    }


def start_rehearsal(
    *,
    package: EducationalPackage,
    scenario: SpeakingScenario,
    discussion_summary: str = "",
    weak_skills: list[str] | tuple[str, ...] | None = None,
) -> tuple[RehearsalState, dict[str, Any]]:
    roles = gpt_rehearsal_roles_for_scenario(scenario)
    gpt_role = roles[0] if roles else "conversation partner"
    context = build_rehearsal_context_payload(
        package=package,
        scenario=scenario,
        discussion_summary=discussion_summary,
        weak_skills=weak_skills,
    )
    opening = _template_opening(scenario, gpt_role)
    state = RehearsalState(
        rehearsal_id=_rehearsal_id(package.package_id),
        package_id=package.package_id,
        scenario=scenario,
        gpt_role=gpt_role,
        turns=[{"role": "assistant", "text": opening}],
        provider=REHEARSAL_PROVIDER_TEMPLATE,
    )
    # voice_session metadata only — GPT is TTS/STT, Claude directs turns via /respond.
    voice = {
        "provider": "gpt-4o-tts",
        "director": REHEARSAL_PROVIDER_CLAUDE,
        "not_hume": True,
        "opening_line": opening,
        "gpt_role": gpt_role,
        "context": context,
    }
    return state, voice


def _template_opening(scenario: SpeakingScenario, gpt_role: str) -> str:
    hook = scenario.continuation_hook or scenario.decision_point
    place = scenario.setting or scenario.story_world or "here"
    if hook:
        return (
            f"[{gpt_role}] We're still in {place}. {hook} "
            f"Try your first line as {scenario.student_role}."
        )
    return (
        f"[{gpt_role}] Continue as {scenario.student_role} in {place}. "
        "Say what you would say next in this case."
    )


def _template_reply(
    *,
    scenario: SpeakingScenario,
    gpt_role: str,
    student_text: str,
    turn_index: int,
) -> dict[str, Any]:
    text = (student_text or "").strip()
    note = None
    correction = None
    if len(text.split()) < 3:
        note = "Try a fuller sentence — same people, same place."
        utterance = (
            f"[{gpt_role}] Take your time. What do you say next about: "
            f"{scenario.decision_point or scenario.continuation_hook}?"
        )
    elif turn_index < 2:
        utterance = (
            f"[{gpt_role}] Good — stay with that. "
            f"Now respond to the next beat: {scenario.continuation_hook or scenario.stakes}"
        )
    else:
        utterance = (
            f"[{gpt_role}] Nice rehearsal. One more: decide how you handle "
            f"{scenario.decision_point or 'the situation'}."
        )
    if text and text[0:1].islower():
        correction = {
            "brief": "Start with a capital when it fits the line.",
            "corrected_form": text[:1].upper() + text[1:],
        }
    return {
        "assistant_utterance": utterance,
        "micro_correction": correction,
        "coaching_note": note,
        "role_in_turn": gpt_role,
    }


async def continue_rehearsal_turn(
    state: RehearsalState,
    *,
    package: EducationalPackage,
    student_text: str,
    discussion_summary: str = "",
    weak_skills: list[str] | tuple[str, ...] | None = None,
    stt_confidence: float | None = None,
    student_cefr: str = "",
    student_memory: dict[str, Any] | None = None,
) -> RehearsalState:
    """One Scene Practice turn. Claude Scene Director reasons; template is the only fallback."""
    text = (student_text or "").strip()
    if not text:
        raise ValueError("empty_response")
    state.turns.append({"role": "student", "text": text})
    context = build_rehearsal_context_payload(
        package=package,
        scenario=state.scenario,
        discussion_summary=discussion_summary,
        weak_skills=weak_skills,
        student_memory=student_memory,
    )
    directed = await direct_scene_turn(
        context=context,
        recent_turns=state.turns[-10:],
        student_transcript=text,
        stt_confidence=stt_confidence,
        student_cefr=student_cefr,
        scene_beat=state.scene_beat or None,
    )

    if directed is None:
        parsed = _template_reply(
            scenario=state.scenario,
            gpt_role=state.gpt_role,
            student_text=text,
            turn_index=len([t for t in state.turns if t.get("role") == "student"]),
        )
        state.provider = REHEARSAL_PROVIDER_TEMPLATE
        utterance = str(parsed.get("assistant_utterance") or "").strip() or _template_opening(
            state.scenario, state.gpt_role
        )
        state.turns.append({"role": "assistant", "text": utterance})
        mc = parsed.get("micro_correction")
        if isinstance(mc, dict):
            brief = str(mc.get("brief") or "").strip()
            form = str(mc.get("corrected_form") or "").strip()
            if brief or form:
                state.corrections.append(f"{brief}: {form}".strip(": "))
        note = parsed.get("coaching_note")
        if isinstance(note, str) and note.strip():
            state.coaching_notes.append(note.strip())
        return state

    state.provider = REHEARSAL_PROVIDER_CLAUDE
    assistant_turn = {"role": "assistant", "text": directed["next_line"]["text"]}
    speaker = str(directed["next_line"].get("speaker") or "").strip()
    if speaker:
        assistant_turn["speaker"] = speaker
    state.turns.append(assistant_turn)
    correction = directed.get("micro_correction")
    if isinstance(correction, dict):
        brief = correction.get("brief") or ""
        form = correction.get("corrected_form") or ""
        if brief or form:
            state.corrections.append(f"{brief}: {form}".strip(": "))
    if directed.get("coaching_note"):
        state.coaching_notes.append(str(directed["coaching_note"]))
    state.evaluations.append(
        {
            "turn_index": len([t for t in state.turns if t.get("role") == "student"]),
            "decision": directed["decision"],
            **directed["evaluation"],
        }
    )
    state.evaluations = state.evaluations[-24:]
    state.scene_beat = directed.get("scene_beat") or state.scene_beat
    return state
