"""Exit rehearsal → LiveConversationContext for Hume EVI (same Educational Case)."""

from __future__ import annotations

import hashlib
from typing import Any

from app.services.language_speaking_live_bridge.types import (
    LiveConversationContext,
    RehearsalState,
    SpeakingScenario,
)


def _context_id(package_id: str, scenario_id: str) -> str:
    digest = hashlib.sha256(f"live:{package_id}:{scenario_id}".encode("utf-8")).hexdigest()[:12]
    return f"lcc_{digest}"


def _last_assistant_line(rehearsal: RehearsalState | None) -> str:
    if rehearsal is None:
        return ""
    for turn in reversed(rehearsal.turns):
        if turn.get("role") == "assistant":
            return str(turn.get("text") or "").strip()
    return ""


def _strip_role_prefix(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("[") and "]" in raw[:40]:
        end = raw.index("]")
        return raw[end + 1 :].strip()
    return raw


def _rehearsal_conversation_summary(rehearsal: RehearsalState | None, *, max_turns: int = 4) -> str:
    if rehearsal is None or not rehearsal.turns:
        return ""
    bits: list[str] = []
    for turn in rehearsal.turns[-max_turns:]:
        role = str(turn.get("role") or "")
        text = _strip_role_prefix(str(turn.get("text") or ""))
        if not text:
            continue
        label = "Student" if role == "student" else "Scene"
        bits.append(f"{label}: {text[:120]}")
    return " | ".join(bits)[:480]


def build_opening_line(scenario: SpeakingScenario, *, rehearsal: RehearsalState | None = None) -> str:
    """Alex must continue the case — never 'Hello, how are you today?'."""
    last_line = _strip_role_prefix(_last_assistant_line(rehearsal))
    chars = [c for c in scenario.characters if c.casefold() != scenario.student_role.casefold()]
    other = chars[0] if chars else "Someone in the scene"
    hook = scenario.continuation_hook or scenario.decision_point
    place = scenario.setting or scenario.story_world

    if last_line:
        return (
            f"Continue exactly where Scene Practice left off. "
            f"{other} is still with you in {place}. "
            f"The scene was: {last_line[:220]} "
            f"What do you say next?"
        ).strip()

    rehearse_bit = ""
    if rehearsal and rehearsal.turns:
        student_turns = [t for t in rehearsal.turns if t.get("role") == "student"]
        if student_turns:
            rehearse_bit = " You just practiced this moment — now live it."
    if hook:
        return (
            f"{other} is still with you in {place}. {hook} "
            f"What do you say next?{rehearse_bit}"
        ).strip()
    return (
        f"Continue as {scenario.student_role} in {place} with "
        f"{', '.join(chars[:3]) or 'the same people'}. What do you say?{rehearse_bit}"
    ).strip()


def build_student_summary(
    scenario: SpeakingScenario,
    *,
    rehearsal: RehearsalState | None = None,
    discussion_summary: str = "",
) -> str:
    parts = [
        f"Prepared as {scenario.student_role} for '{scenario.story_title}'.",
        f"Decision: {scenario.decision_point}" if scenario.decision_point else "",
    ]
    if discussion_summary.strip():
        parts.append(f"Discussion: {discussion_summary.strip()[:220]}")
    if rehearsal:
        n = len([t for t in rehearsal.turns if t.get("role") == "student"])
        parts.append(f"Scene Practice turns: {n}.")
        convo = _rehearsal_conversation_summary(rehearsal)
        if convo:
            parts.append(f"Scene summary: {convo}")
        last = _strip_role_prefix(_last_assistant_line(rehearsal))
        if last:
            parts.append(f"Scene stopped at: {last[:180]}")
        if rehearsal.coaching_notes:
            parts.append(f"Coach notes: {'; '.join(rehearsal.coaching_notes[-2:])}")
    return " ".join(p for p in parts if p).strip()


def estimate_confidence(rehearsal: RehearsalState | None) -> str:
    if rehearsal is None:
        return "building"
    student_turns = [t for t in rehearsal.turns if t.get("role") == "student"]
    if len(student_turns) >= 3 and len(rehearsal.corrections) <= 1:
        return "ready"
    if len(student_turns) >= 1:
        return "building"
    return "needs_support"


def remaining_weaknesses(
    *,
    rehearsal: RehearsalState | None,
    weak_skills: list[str] | tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    out: list[str] = []
    if rehearsal:
        for c in rehearsal.corrections[-3:]:
            if c and c not in out:
                out.append(c)
        for n in rehearsal.coaching_notes[-2:]:
            if n and n not in out:
                out.append(n)
    for w in weak_skills or ():
        s = str(w or "").strip()
        if s and s not in out:
            out.append(s)
    return tuple(out[:6])


def build_live_conversation_context(
    scenario: SpeakingScenario,
    *,
    rehearsal: RehearsalState | None = None,
    discussion_summary: str = "",
    weak_skills: list[str] | tuple[str, ...] | None = None,
) -> LiveConversationContext:
    opening = build_opening_line(scenario, rehearsal=rehearsal)
    notes = tuple((rehearsal.coaching_notes[-4:] if rehearsal else []) or ())
    last_scene = _strip_role_prefix(_last_assistant_line(rehearsal))
    if last_scene and last_scene not in notes:
        notes = (*notes, f"Scene cursor: {last_scene[:200]}")[:5]
    return LiveConversationContext(
        context_id=_context_id(scenario.package_id, scenario.scenario_id),
        package_id=scenario.package_id,
        story_world=scenario.story_world or scenario.setting,
        story_title=scenario.story_title,
        characters=scenario.characters,
        stakes=scenario.stakes,
        decision_point=scenario.decision_point,
        continuation_hook=scenario.continuation_hook,
        opening_line=opening,
        student_summary=build_student_summary(
            scenario, rehearsal=rehearsal, discussion_summary=discussion_summary
        ),
        grammar_focus=scenario.grammar_focus,
        vocabulary_focus=scenario.vocabulary_focus,
        objectives=scenario.objectives,
        student_confidence=estimate_confidence(rehearsal),
        remaining_weaknesses=remaining_weaknesses(
            rehearsal=rehearsal, weak_skills=weak_skills
        ),
        case_category=scenario.case_category,
        case_archetype=scenario.case_archetype,
        stakeholders=scenario.stakeholders,
        continuity_fingerprint=scenario.continuity_fingerprint,
        rehearsal_notes=notes,
    )


def merge_live_context_into_alex_dict(
    alex: dict[str, Any],
    live: LiveConversationContext,
) -> dict[str, Any]:
    """Overlay LiveConversationContext onto tutor alex_context without inventing curriculum."""
    out = dict(alex)
    out["case_title"] = live.story_title or out.get("case_title") or ""
    out["case_setting"] = live.story_world or out.get("case_setting") or ""
    out["case_characters"] = list(live.characters) or list(out.get("case_characters") or [])
    out["case_conflict"] = live.stakes or out.get("case_conflict") or ""
    out["case_continuation_hook"] = live.continuation_hook or out.get("case_continuation_hook") or ""
    out["case_decision_point"] = live.decision_point or out.get("case_decision_point") or ""
    out["case_category"] = live.case_category or out.get("case_category") or ""
    out["case_archetype"] = live.case_archetype or out.get("case_archetype") or ""
    out["case_stakeholders"] = list(live.stakeholders) or list(out.get("case_stakeholders") or [])
    out["current_task_instruction"] = live.continuation_hook or out.get("current_task_instruction") or ""
    out["communicative_scenario"] = live.continuation_hook or out.get("communicative_scenario") or ""
    out["live_conversation_opening"] = live.opening_line
    out["live_conversation_context"] = live.to_dict()
    out["live_bridge_ready"] = True
    # Prefer case-grounded task context line
    if live.story_title and live.characters:
        out["task_context"] = (
            f"{live.story_title} · {live.story_world} · {', '.join(live.characters[:4])}"
            + (f" · decision: {live.decision_point}" if live.decision_point else "")
        )
    return out
