"""Build SpeakingScenario from a frozen Educational Package (same world)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.services.language_educational_package.types import EducationalPackage
from app.services.language_speaking_live_bridge.continuity import (
    continuity_fingerprint_for_package,
    extract_case_continuity_fields,
)
from app.services.language_speaking_live_bridge.types import SpeakingScenario


def _short_id(package_id: str, salt: str) -> str:
    digest = hashlib.sha256(f"{package_id}:{salt}".encode("utf-8")).hexdigest()[:12]
    return f"scn_{digest}"


def _pick_student_role(characters: list[str], stakeholders: list[str]) -> str:
    """Student acts as the primary protagonist (first named character when present)."""
    for name in characters:
        n = str(name or "").strip()
        if n:
            return n
    for name in stakeholders:
        n = str(name or "").strip()
        if n:
            return n
    return "you"


def _pick_gpt_roles(characters: list[str], student_role: str) -> list[str]:
    roles = [c for c in characters if c.strip() and c.strip().casefold() != student_role.casefold()]
    return roles[:4] if roles else ["conversation partner"]


def _infer_must_do(*, decision_point: str, continuation_hook: str, conflict: str) -> list[str]:
    """Derive concrete speaking actions from the decision + continuation (no new world)."""
    actions: list[str] = []
    hook = (continuation_hook or "").strip()
    decision = (decision_point or "").strip()
    if hook:
        # Split lightly on "and" / commas for actionable bullets
        chunks = re.split(r"[.;]|,\s*and\s+|\s+and\s+", hook)
        for chunk in chunks:
            text = chunk.strip(" ,.").strip()
            if len(text) >= 12:
                actions.append(text[:160])
            if len(actions) >= 4:
                break
    if decision and decision not in actions:
        actions.append(f"Address the decision: {decision[:140]}")
    if not actions and conflict:
        actions.append(f"Respond to the situation: {conflict[:140]}")
    if not actions:
        actions.append("Continue the Educational Case in the same place with the same people")
    return actions[:5]


def build_student_brief(
    *,
    student_role: str,
    setting: str,
    characters: list[str],
    stakes: str,
    decision_point: str,
    continuation_hook: str,
    must_do: list[str],
) -> str:
    others = [c for c in characters if c.casefold() != student_role.casefold()]
    others_line = ", ".join(others[:4]) if others else "the people already in this case"
    place = setting or "the same place from the story"
    lines = [
        f"You are {student_role}.",
        f"{others_line} {'are' if others and len(others) != 1 else 'is'} with you in {place}."
        if others
        else f"You are in {place}.",
        stakes.strip() if stakes.strip() else "",
        f"Decision point: {decision_point}" if decision_point else "",
        f"What happens next: {continuation_hook}" if continuation_hook else "",
    ]
    if must_do:
        lines.append("You need to:")
        for item in must_do:
            lines.append(f"— {item}")
    return "\n".join(line for line in lines if line).strip()


def build_speaking_scenario(
    package: EducationalPackage,
    *,
    weak_skills: list[str] | tuple[str, ...] | None = None,
) -> SpeakingScenario:
    """Create preparation scenario from the authored Educational Case only."""
    fields = extract_case_continuity_fields(package)
    package_id = str(getattr(package, "package_id", "") or "")
    spine = package.story_spine
    student_role = _pick_student_role(list(fields["characters"]), list(fields.get("stakeholders") or []))
    must_do = _infer_must_do(
        decision_point=str(fields["decision_point"]),
        continuation_hook=str(fields["continuation_hook"]),
        conflict=str(fields["conflict"]),
    )
    # Surface weak skills as soft prep reminders without inventing content
    if weak_skills:
        for w in list(weak_skills)[:2]:
            label = str(w or "").strip()
            if label and label not in must_do:
                must_do.append(f"Watch for: {label}")

    brief = build_student_brief(
        student_role=student_role,
        setting=str(fields["story_world"]),
        characters=list(fields["characters"]),
        stakes=str(fields["stakes"] or fields["conflict"]),
        decision_point=str(fields["decision_point"]),
        continuation_hook=str(fields["continuation_hook"]),
        must_do=must_do,
    )

    return SpeakingScenario(
        scenario_id=_short_id(package_id, "scenario"),
        package_id=package_id,
        student_role=student_role,
        student_brief=brief,
        setting=str(fields["story_world"] or spine.setting),
        story_title=str(fields["story_title"]),
        story_world=str(fields["story_world"]),
        characters=tuple(fields["characters"]),
        stakes=str(fields["stakes"] or fields["conflict"]),
        decision_point=str(fields["decision_point"]),
        continuation_hook=str(fields["continuation_hook"]),
        must_do=tuple(must_do),
        vocabulary_focus=tuple(fields["vocabulary"][:12]),
        grammar_focus=tuple(fields["grammar"][:8]),
        objectives=tuple(fields["objectives"][:8]),
        case_category=str(fields["case_category"] or spine.case_category),
        case_archetype=str(fields["case_archetype"] or spine.case_archetype),
        stakeholders=tuple(fields.get("stakeholders") or spine.stakeholders or ()),
        continuity_fingerprint=continuity_fingerprint_for_package(package),
    )


def gpt_rehearsal_roles_for_scenario(scenario: SpeakingScenario) -> list[str]:
    return _pick_gpt_roles(list(scenario.characters), scenario.student_role)


def scenario_to_prep_projection(scenario: SpeakingScenario) -> dict[str, Any]:
    """Student-facing preparation panel payload."""
    return {
        "scenario_id": scenario.scenario_id,
        "package_id": scenario.package_id,
        "student_role": scenario.student_role,
        "student_brief": scenario.student_brief,
        "setting": scenario.setting,
        "story_title": scenario.story_title,
        "characters": list(scenario.characters),
        "stakes": scenario.stakes,
        "decision_point": scenario.decision_point,
        "continuation_hook": scenario.continuation_hook,
        "must_do": list(scenario.must_do),
        "vocabulary_focus": list(scenario.vocabulary_focus),
        "grammar_focus": list(scenario.grammar_focus),
        "objectives": list(scenario.objectives),
        "case_category": scenario.case_category,
        "case_archetype": scenario.case_archetype,
        "gpt_roles": gpt_rehearsal_roles_for_scenario(scenario),
        "continuity_fingerprint": scenario.continuity_fingerprint,
    }
