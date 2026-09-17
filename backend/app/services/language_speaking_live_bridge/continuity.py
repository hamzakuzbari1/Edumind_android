"""Same-world continuity fingerprint for Educational Case → live bridge."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _unique_preserve(values: list[Any] | tuple[Any, ...] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values or []:
        s = str(v or "").strip()
        if not s or s.casefold() in seen:
            continue
        seen.add(s.casefold())
        out.append(s)
    return out


def _sorted_unique(values: list[Any] | tuple[Any, ...] | None) -> list[str]:
    return sorted(_unique_preserve(values), key=str.casefold)


def extract_case_continuity_fields(package: Any) -> dict[str, Any]:
    """Pull the continuity-critical fields from an EducationalPackage-like object."""
    spine = getattr(package, "story_spine", None)
    material = getattr(package, "input_material", None)
    title = str(
        (getattr(spine, "title", None) if spine is not None else None)
        or (getattr(material, "title", None) if material is not None else None)
        or getattr(package, "title", None)
        or ""
    )
    world = ""
    conflict = ""
    decision = ""
    hook = ""
    characters: list[str] = []
    stakes = ""
    case_category = ""
    case_archetype = ""
    stakeholders: list[str] = []
    if spine is not None:
        world = str(getattr(spine, "setting", None) or getattr(spine, "context", None) or "")
        conflict = str(getattr(spine, "conflict", None) or getattr(spine, "problem", None) or "")
        decision = str(getattr(spine, "decision_point", None) or "")
        hook = str(getattr(spine, "continuation_hook", None) or "")
        chars = getattr(spine, "characters", None) or ()
        if isinstance(chars, (list, tuple)):
            for c in chars:
                if hasattr(c, "name"):
                    characters.append(str(getattr(c, "name") or ""))
                else:
                    characters.append(str(c or ""))
        stakes = str(getattr(spine, "consequences", None) or conflict)
        case_category = str(getattr(spine, "case_category", None) or "")
        case_archetype = str(getattr(spine, "case_archetype", None) or "")
        stakes_list = getattr(spine, "stakeholders", None) or ()
        if isinstance(stakes_list, (list, tuple)):
            stakeholders = [str(s) for s in stakes_list if str(s).strip()]

    constraints = getattr(package, "constraints", None)
    if constraints is not None and hasattr(constraints, "to_dict"):
        try:
            constraints = constraints.to_dict()
        except Exception:
            constraints = {}
    if not isinstance(constraints, dict):
        constraints = {}

    vocab_raw = list(constraints.get("target_vocabulary") or [])
    if not vocab_raw:
        vic = getattr(package, "vocabulary_in_context", None)
        entries = getattr(vic, "entries", None) if vic is not None else None
        if isinstance(entries, (list, tuple)):
            vocab_raw = [
                str(getattr(e, "surface", None) or getattr(e, "lemma", None) or "")
                for e in entries
            ]
    grammar_raw = list(constraints.get("target_grammar") or [])
    if not grammar_raw:
        gic = getattr(package, "grammar_in_context", None)
        gentries = getattr(gic, "entries", None) if gic is not None else None
        if isinstance(gentries, (list, tuple)):
            grammar_raw = [
                str(getattr(e, "label", None) or getattr(e, "pattern", None) or "")
                for e in gentries
            ]
    objectives_raw = list(constraints.get("objectives") or [])
    if not objectives_raw:
        objs = getattr(package, "objectives", None)
        if isinstance(objs, (list, tuple)):
            objectives_raw = [str(o) for o in objs]
        elif objs is not None and hasattr(objs, "items"):
            items = getattr(objs, "items", None) or ()
            objectives_raw = [
                str(getattr(o, "text", None) or getattr(o, "label", None) or o) for o in items
            ]

    case_category = case_category or str(
        constraints.get("case_category") or getattr(package, "case_category", None) or ""
    )
    case_archetype = case_archetype or str(
        constraints.get("case_archetype") or getattr(package, "case_archetype", None) or ""
    )

    return {
        "story_title": title,
        "story_world": world,
        "conflict": conflict,
        "decision_point": decision,
        "continuation_hook": hook,
        "characters": _unique_preserve(characters),
        "stakes": stakes or conflict,
        "stakeholders": _unique_preserve(stakeholders),
        "vocabulary": _unique_preserve([str(v) for v in vocab_raw]),
        "grammar": _unique_preserve([str(g) for g in grammar_raw]),
        "objectives": _unique_preserve([str(o) for o in objectives_raw]),
        "case_category": case_category,
        "case_archetype": case_archetype,
    }


def continuity_fingerprint_from_fields(fields: dict[str, Any]) -> str:
    payload = {
        "story_title": fields.get("story_title") or "",
        "story_world": fields.get("story_world") or "",
        "conflict": fields.get("conflict") or "",
        "decision_point": fields.get("decision_point") or "",
        "continuation_hook": fields.get("continuation_hook") or "",
        "characters": fields.get("characters") or [],
        "vocabulary": fields.get("vocabulary") or [],
        "grammar": fields.get("grammar") or [],
        "objectives": fields.get("objectives") or [],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def continuity_fingerprint_for_package(package: Any) -> str:
    return continuity_fingerprint_from_fields(extract_case_continuity_fields(package))


def assert_same_world(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    label: str = "stages",
) -> list[str]:
    """Return list of continuity violations (empty = ok)."""
    errors: list[str] = []
    keys = (
        "story_world",
        "decision_point",
        "continuation_hook",
        "conflict",
    )
    for key in keys:
        a = str(left.get(key) or "").strip().casefold()
        b = str(right.get(key) or "").strip().casefold()
        if a and b and a != b:
            errors.append(f"{label}: {key} mismatch")
    lc = set(_sorted_unique(left.get("characters")))
    rc = set(_sorted_unique(right.get("characters")))
    if lc and rc and not (lc & rc):
        errors.append(f"{label}: characters share no overlap")
    return errors
