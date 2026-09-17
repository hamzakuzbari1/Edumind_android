"""Personalization Engine — adapt HOW students experience an Educational Case.

Curriculum Engine remains the sole owner of CEFR, vocabulary, grammar, objectives,
difficulty, case_category, and case_archetype.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from app.services.language_speaking_case_personalization.themes import (
    age_band,
    alternate_setting,
    culture_name_pool,
    learning_style_dialogue,
    match_interest_pack,
    match_profession_pack,
)
from app.services.language_speaking_case_personalization.types import (
    CURRICULUM_LOCKED_KEYS,
    PERSONALIZATION_ENGINE_VERSION,
    PersonalizationDirective,
    StudentCaseSignals,
)
from app.services.language_speaking_case_personalization.validation import (
    PersonalizationGuardError,
    assert_curriculum_unchanged,
    snapshot_curriculum_fields,
)


def _profile_fingerprint(signals: StudentCaseSignals) -> str:
    payload = {
        "age": signals.age,
        "occupation": signals.occupation,
        "future_goal": signals.future_goal,
        "learning_style": signals.learning_style,
        "explanation_style": signals.explanation_style,
        "interests": sorted(signals.interests),
        "hobbies": sorted(signals.hobbies),
        "favorite_topics": sorted(signals.favorite_topics),
        "avoided_topics": sorted(signals.avoided_topics),
        "used_theme_keys": list(signals.used_theme_keys)[-8:],
        "used_settings": list(signals.used_settings)[-8:],
        "culture_hint": signals.culture_hint,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _merge_character_names(
    *,
    existing: list[str],
    pack_names: list[str],
    culture_names: tuple[str, ...],
    need: int,
) -> list[str]:
    out: list[str] = []
    for name in [*pack_names, *culture_names, *existing]:
        n = str(name).strip()
        if n and n not in out:
            out.append(n)
        if len(out) >= need:
            break
    while len(out) < max(2, need):
        out.append(f"Speaker{len(out)+1}")
    return out[: max(need, 2)]


def build_personalization_directive(
    constraints_payload: dict[str, Any],
    signals: StudentCaseSignals,
) -> PersonalizationDirective:
    """Build experience overlays from signals + frozen curriculum category."""
    category = str(
        constraints_payload.get("case_category")
        or (constraints_payload.get("story_complexity_policy") or {}).get("case_category")
        or ""
    )
    complexity = constraints_payload.get("story_complexity_policy") or {}
    char_min = int(complexity.get("characters_min") or 2)

    theme_key, interest_pack = match_interest_pack(
        interests=signals.interests,
        hobbies=signals.hobbies,
        favorite_topics=signals.favorite_topics,
        avoided_topics=signals.avoided_topics,
        used_theme_keys=signals.used_theme_keys,
    )
    profession_key, profession_pack = match_profession_pack(
        occupation=signals.occupation,
        future_goal=signals.future_goal,
        used_theme_keys=signals.used_theme_keys,
    )
    # Prefer profession when no strong interest match; otherwise interest first.
    pack = interest_pack or profession_pack
    active_theme = theme_key or profession_key
    if interest_pack is None and profession_pack is not None:
        pack = profession_pack
        active_theme = profession_key

    band = age_band(signals.age)
    dialogue, framing = learning_style_dialogue(
        signals.learning_style, signals.explanation_style
    )
    culture_names = culture_name_pool(signals.culture_hint, signals.locale)

    base_setting = str(constraints_payload.get("scenario_type") or "everyday")
    setting = alternate_setting(base_setting, signals.used_settings)
    title = str(constraints_payload.get("story_title_hint") or "")
    world = str(constraints_payload.get("story_world") or "")
    roles: list[str] = []
    names: list[str] = list(constraints_payload.get("character_hints") or [])
    interest_labels: list[str] = []
    discussion_hooks: list[str] = []
    memory_blocked = list(signals.used_settings)[:12]

    progression_locked = bool(constraints_payload.get("curriculum_progression"))
    if pack:
        interest_labels = [str(x) for x in (pack.get("labels") or ())[:4]]
        roles = [str(r) for r in (pack.get("roles") or ()) if r]
        names = _merge_character_names(
            existing=names,
            pack_names=[str(n) for n in (pack.get("names") or ())],
            culture_names=culture_names,
            need=char_min,
        )
        framing = str(pack.get("emotional") or framing)
        if pack.get("discussion"):
            interest = interest_labels[0] if interest_labels else active_theme
            discussion_hooks.append(
                f"You mentioned interest in {interest}. {pack['discussion']}"
            )
        if progression_locked:
            # M9 — keep Curriculum Graph case shell; only flavor details
            setting = alternate_setting(base_setting, signals.used_settings)
            world = (
                f"{world} Personal flavor: adapt examples toward {interest_labels[0]} "
                f"only when natural. Do not leave this Educational Case world."
            ).strip()
        else:
            setting = alternate_setting(
                str(pack.get("setting") or setting), signals.used_settings
            )
            title = str(pack.get("title") or title)
            world = (
                f"{pack.get('world')} This remains a {category.replace('_', ' ') or 'speaking'} "
                f"Educational Case. Keep the learning focus "
                f"'{constraints_payload.get('learning_focus')}' unchanged."
            )
    else:
        # Light culture/age personalization without forcing hobbies
        names = _merge_character_names(
            existing=names,
            pack_names=[],
            culture_names=culture_names,
            need=char_min,
        )
        if band == "teen":
            world = (
                f"{world} Frame characters as young people / students facing a realistic "
                f"spoken decision — still the same Educational Case category."
            ).strip()
        elif band == "mid_career":
            world = (
                f"{world} Frame characters with workplace or family responsibility pressure."
            ).strip()

    # Avoid title collisions with previously completed cases
    for used_title in signals.completed_case_titles:
        if title and title.lower() == used_title.lower():
            title = f"{title} — New Angle"
            break

    alex_notes: list[str] = [
        "Continue ONLY this Educational Case world — never invent a new situation.",
    ]
    if interest_labels:
        alex_notes.append(
            f"Student interests include {', '.join(interest_labels[:3])}; "
            f"reference them only when natural inside this case."
        )
    if signals.weak_skill_labels:
        alex_notes.append(
            f"Gently elicit clearer speech related to: {', '.join(signals.weak_skill_labels[:3])}."
        )
    if signals.recent_mistake_tags:
        alex_notes.append(
            f"Student recent speaking slips include: {', '.join(signals.recent_mistake_tags[:3])}."
        )
    if signals.learning_style:
        alex_notes.append(f"Prefer a {signals.learning_style} coaching feel.")

    return PersonalizationDirective(
        engine_version=PERSONALIZATION_ENGINE_VERSION,
        profile_fingerprint=_profile_fingerprint(signals),
        theme_key=active_theme,
        profession_key=profession_key,
        age_band=band,
        interest_labels=tuple(interest_labels),
        setting_overlay=setting,
        story_world_overlay=world,
        story_title_hint=title,
        character_names=tuple(names[: max(char_min, 2)]),
        character_roles=tuple(roles),
        cultural_style=signals.culture_hint or ("arabic_levant" if signals.locale.startswith("ar") else "international"),
        emotional_framing=framing,
        dialogue_style=dialogue,
        learning_style_hint=signals.learning_style or "",
        discussion_interest_hooks=tuple(discussion_hooks),
        alex_notes=tuple(alex_notes),
        avoided_settings=tuple(signals.used_settings[:12]),
        memory_reuse_blocked=tuple(memory_blocked),
        applied=True,
    )


def signals_are_substantive(signals: StudentCaseSignals) -> bool:
    """True when there is enough student signal to justify experience adaptation."""
    goal = (signals.future_goal or "").strip().lower()
    return bool(
        signals.interests
        or signals.hobbies
        or signals.favorite_topics
        or signals.occupation
        or (goal and goal not in {"undecided", "none", "n/a"})
        or signals.used_settings
        or signals.completed_case_titles
        or signals.used_theme_keys
        or signals.age is not None
        or signals.learning_style
        or signals.explanation_style
        or signals.weak_skill_labels
        or signals.recent_mistake_tags
        or signals.culture_hint
    )


def apply_case_personalization(
    constraints_payload: dict[str, Any],
    signals: StudentCaseSignals | dict[str, Any] | None,
) -> dict[str, Any]:
    """Overlay experience fields after Curriculum enrichment.

    Raises PersonalizationGuardError if any locked curriculum field would change.
    """
    if not isinstance(constraints_payload, dict):
        raise ValueError("constraints_payload must be a dict")
    if signals is None:
        return dict(constraints_payload)
    sig = (
        signals
        if isinstance(signals, StudentCaseSignals)
        else StudentCaseSignals.from_dict(signals)
    )
    if not signals_are_substantive(sig):
        return dict(constraints_payload)

    before = snapshot_curriculum_fields(constraints_payload)
    out = copy.deepcopy(constraints_payload)
    directive = build_personalization_directive(out, sig)

    # Experience-only overlays
    if directive.setting_overlay:
        out["scenario_type"] = directive.setting_overlay
    if directive.story_world_overlay:
        out["story_world"] = directive.story_world_overlay
    if directive.story_title_hint:
        out["story_title_hint"] = directive.story_title_hint
    if directive.character_names:
        # Keep curriculum cast size band by not shrinking below existing hints length
        need = max(len(out.get("character_hints") or []), len(directive.character_names))
        names = list(directive.character_names)
        while len(names) < need and len(out.get("character_hints") or []) > len(names):
            for n in out.get("character_hints") or []:
                if n not in names:
                    names.append(n)
                if len(names) >= need:
                    break
        out["character_hints"] = names
        # Soft rename first stakeholders to personalized people + keep institutional ones
        stakes = list(out.get("stakeholder_hints") or [])
        personalized = list(names)
        for s in stakes:
            if s not in personalized and s.lower() not in {n.lower() for n in names}:
                personalized.append(s)
        out["stakeholder_hints"] = personalized[: max(len(stakes), len(names))]

    # Communicative goal: keep educational intent, add personal flavor without changing objective text
    goal = str(out.get("communicative_goal") or "").strip()
    if directive.interest_labels and goal:
        out["communicative_goal"] = (
            f"{goal} Use examples that fit a {directive.interest_labels[0]} context "
            f"when natural — without changing the language targets."
        )

    out["personalization"] = directive.to_dict()
    out["personalization_engine_version"] = PERSONALIZATION_ENGINE_VERSION

    # Harden: locked curriculum keys must match pre-personalization snapshot
    after = snapshot_curriculum_fields(out)
    try:
        assert_curriculum_unchanged(before, after)
    except PersonalizationGuardError:
        # Roll back any accidental mutation by restoring locked keys from snapshot
        for key in CURRICULUM_LOCKED_KEYS:
            if key in before:
                out[key] = copy.deepcopy(before[key])
        after = snapshot_curriculum_fields(out)
        assert_curriculum_unchanged(before, after)

    return out
