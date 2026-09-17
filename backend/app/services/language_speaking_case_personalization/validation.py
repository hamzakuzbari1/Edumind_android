"""Guardrails — personalization must never seize curriculum ownership."""

from __future__ import annotations

import copy
from typing import Any

from app.services.language_speaking_case_personalization.types import CURRICULUM_LOCKED_KEYS


class PersonalizationGuardError(ValueError):
    """Raised when personalization mutates a curriculum-owned field."""


def snapshot_curriculum_fields(payload: dict[str, Any]) -> dict[str, Any]:
    snap: dict[str, Any] = {}
    for key in CURRICULUM_LOCKED_KEYS:
        if key in payload:
            snap[key] = copy.deepcopy(payload[key])
    # Nested locks inside story_complexity_policy when present
    complexity = payload.get("story_complexity_policy")
    if isinstance(complexity, dict):
        nested = {
            k: complexity.get(k)
            for k in (
                "case_category",
                "case_archetype",
                "decision_complexity",
                "ethical_complexity",
                "min_words",
                "max_words",
                "required_grammar_topic_count",
                "reflection_depth",
                "discussion_depth",
                "reading_complexity",
                "sentence_complexity",
            )
            if k in complexity
        }
        snap["_complexity_core"] = nested
    return snap


def assert_curriculum_unchanged(before: dict[str, Any], after: dict[str, Any]) -> None:
    for key, value in before.items():
        if after.get(key) != value:
            raise PersonalizationGuardError(
                f"personalization_mutated_curriculum:{key}"
            )


def personalization_is_experience_only(payload: dict[str, Any]) -> bool:
    """True when a personalization block is present and curriculum fields look intact."""
    perso = payload.get("personalization")
    if not isinstance(perso, dict) or not perso.get("applied"):
        return True
    # Structural sanity: locked keys exist if curriculum ran
    if payload.get("vocabulary_targets") is None and payload.get("vocabulary_ids") is None:
        return True
    return bool(payload.get("case_category") or payload.get("story_complexity_policy"))
