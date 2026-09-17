"""Deterministic authoring request fingerprints (V1.3) — replayability."""

from __future__ import annotations

import hashlib
import json

from app.services.language_grammar_activity_authoring.types import AuthoringRequest


def fingerprint_authoring_request(request: AuthoringRequest) -> str:
    """Stable fingerprint of authoring inputs (excludes ephemeral request_id noise if empty)."""
    ctx = request.context
    payload = {
        "grammar_targets": list(ctx.grammar_targets),
        "student_cefr": ctx.student_cefr,
        "learning_objective": ctx.learning_objective,
        "teacher_persona": {
            "persona_id": ctx.teacher_persona.persona_id,
            "tone": ctx.teacher_persona.tone,
        },
        "student_profile": {
            "student_id": ctx.student_profile.student_id,
            "language_id": ctx.student_profile.language_id,
            "overall_cefr": ctx.student_profile.overall_cefr,
            "locale": ctx.student_profile.locale,
        },
        "lesson_context": {
            "lesson_id": ctx.lesson_context.lesson_id,
            "step_id": ctx.lesson_context.step_id,
            "context_hint": ctx.lesson_context.context_hint,
        },
        "activity_type": ctx.activity_type,
        "localization": ctx.localization,
        "difficulty": ctx.difficulty.value,
        "versions": {
            "catalog_version": ctx.versions.catalog_version,
            "grammar_schema_version": ctx.versions.grammar_schema_version,
            "blueprint_version": ctx.versions.blueprint_version,
            "activity_schema_version": ctx.versions.activity_schema_version,
            "planner_version": ctx.versions.planner_version,
            "provider_version": ctx.versions.provider_version,
            "authoring_version": ctx.versions.authoring_version,
        },
        "preferred_strategy_id": ctx.preferred_strategy_id,
        "adaptive": ctx.adaptive.to_prompt_dict(),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
