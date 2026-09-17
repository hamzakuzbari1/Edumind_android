"""Deterministic blueprint hash (W3.1) — auditing and debugging only."""

from __future__ import annotations

import hashlib
import json

from app.services.language_writing_lesson_planner.types import WritingLessonBlueprint


def canonical_blueprint_payload(blueprint: WritingLessonBlueprint) -> dict[str, object]:
    """Educational payload for hashing — excludes blueprint_hash itself."""
    payload = blueprint.to_dict()
    payload.pop("blueprint_hash", None)
    return payload


def compute_blueprint_hash(blueprint: WritingLessonBlueprint) -> str:
    """Same educational blueprint -> same hash (SHA-256 hex)."""
    canonical = json.dumps(canonical_blueprint_payload(blueprint), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
