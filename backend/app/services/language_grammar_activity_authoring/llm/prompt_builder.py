"""Adaptive Prompt Builder for Grammar Lesson Authoring (V1.7).

Owns system / developer / user prompts. Providers never build prompts inline.
"""

from __future__ import annotations

import json

from app.services.language_grammar_activity_authoring.llm.lesson_schema import LESSON_PACKAGE_VERSION, LESSON_SCHEMA_VERSION
from app.services.language_grammar_activity_authoring.llm.templates import (
    DEVELOPER_PROMPT_TEMPLATE,
    PROMPT_VERSION,
    REQUIRED_SECTIONS_CSV,
    SCHEMA_HINT,
    SYSTEM_PROMPT_TEMPLATE,
    USER_PROMPT_TEMPLATE,
)
from app.services.language_grammar_activity_authoring.llm.types import PromptBundle
from app.services.language_grammar_activity_authoring.types import AuthoringRequest


def _j(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _topic_profile(ctx) -> dict[str, object]:  # noqa: ANN001 - keeps local prompt code compact
    raw = ctx.extras.get("grammar_profile_json")
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            return parsed
    return {
        "selected_grammar_target": ctx.grammar_targets[0] if ctx.grammar_targets else "",
        "display_name": ctx.grammar_targets[0] if ctx.grammar_targets else "Grammar",
        "cefr_level": ctx.student_cefr,
        "learning_objectives": [ctx.learning_objective],
        "canonical_patterns": list(ctx.grammar_targets),
        "model_examples": [],
        "common_mistakes": [],
        "teaching_notes": "",
        "focus_note": "",
        "recommended_contexts": [],
        "arabic_speaker_misconceptions": [],
        "prerequisite_reminders": [],
    }


def build_prompt_bundle(
    request: AuthoringRequest,
    *,
    provider_id: str = "claude",
    provider_version: str = "1.7.0",
) -> PromptBundle:
    """Build PromptBundle — adapts HOW to teach, never WHAT grammar."""
    ctx = request.context
    locale = ctx.localization or ctx.student_profile.locale or "en"
    versions = ctx.versions
    grammar_targets = list(ctx.grammar_targets)
    topic_profile = _topic_profile(ctx)
    authoring_input = {
        "selected_grammar_target": grammar_targets[0] if grammar_targets else "",
        "grammar_display_name": topic_profile.get("display_name") or (grammar_targets[0] if grammar_targets else ""),
        "cefr_level": ctx.student_cefr,
        "learner_language": "Arabic",
        "lesson_language": "English",
        "support_language": "Arabic",
        "learning_objectives": topic_profile.get("learning_objectives") or [ctx.learning_objective],
        "topic_teaching_profile": {
            "canonical_patterns": topic_profile.get("canonical_patterns") or grammar_targets,
            "model_examples": topic_profile.get("model_examples") or [],
            "common_mistakes": topic_profile.get("common_mistakes") or [],
            "teaching_notes": topic_profile.get("teaching_notes") or "",
            "focus_note": topic_profile.get("focus_note") or "",
            "recommended_contexts": topic_profile.get("recommended_contexts") or [],
            "arabic_speaker_misconceptions": topic_profile.get("arabic_speaker_misconceptions") or [],
            "prerequisite_reminders": topic_profile.get("prerequisite_reminders") or [],
            "support_grammar_targets": topic_profile.get("support_grammar_targets") or [],
        },
        "optional_learner_signals": ctx.adaptive.to_prompt_dict(),
    }

    variables = {
        "prompt_version": PROMPT_VERSION,
        "lesson_schema_version": str(LESSON_SCHEMA_VERSION),
        "lesson_package_version": LESSON_PACKAGE_VERSION,
        "required_sections": REQUIRED_SECTIONS_CSV,
        "authoring_input_json": _j(authoring_input),
        "provider_id": provider_id,
        "provider_version": provider_version,
        "localization": locale,
        "catalog_version": versions.catalog_version,
        "grammar_schema_version": str(versions.grammar_schema_version),
    }

    system_prompt = SYSTEM_PROMPT_TEMPLATE.strip()
    developer_prompt = DEVELOPER_PROMPT_TEMPLATE.format(**variables).strip()
    user_prompt = (
        USER_PROMPT_TEMPLATE.format(**variables).strip()
        + "\n\nSchema hint:\n"
        + _j(SCHEMA_HINT)
    )

    return PromptBundle(
        system_prompt=system_prompt,
        developer_prompt=developer_prompt,
        user_prompt=user_prompt,
        prompt_version=PROMPT_VERSION,
        localization=locale,
        variables={k: str(v) for k, v in variables.items()},
    )
