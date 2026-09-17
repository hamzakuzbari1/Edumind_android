"""Deterministic blueprint hash (S9)."""

from __future__ import annotations

import hashlib
import json

from app.services.language_speaking_lesson_planner.types import SpeakingLessonBlueprint


def canonical_blueprint_payload(blueprint: SpeakingLessonBlueprint) -> dict[str, object]:
    payload = blueprint.to_dict()
    payload.pop("blueprint_hash", None)
    return payload


def compute_blueprint_hash(blueprint: SpeakingLessonBlueprint) -> str:
    canonical = json.dumps(canonical_blueprint_payload(blueprint), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
