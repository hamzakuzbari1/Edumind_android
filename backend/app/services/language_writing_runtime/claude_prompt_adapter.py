"""Adapt WritingPromptBundle to Claude system/user prompts (W6) — no educational logic."""

from __future__ import annotations

from app.services.language_writing_generation.prompt_builder_types import PromptSectionKey, WritingPromptBundle

_JSON_OUTPUT_SCHEMA = """
Return a single JSON object with these keys (student-facing wording only):
{
  "mission_title": "string",
  "writing_context": "string",
  "instructions": ["string"],
  "writing_prompt": "string",
  "constraints": ["string"],
  "checklist": ["string"],
  "tips": ["string"],
  "learning_outcomes": ["string"],
  "success_criteria": ["string"],
  "expected_output": "string",
  "grammar_display": "string",
  "vocabulary_display": "string"
}
Preserve all educational targets exactly. Rephrase for clarity only.
"""


def prompt_bundle_to_claude_messages(bundle: WritingPromptBundle) -> tuple[str, str]:
    """Convert frozen prompt sections to Claude system + user prompts."""
    system_parts = [
        bundle.section(PromptSectionKey.system),
        bundle.section(PromptSectionKey.role),
        bundle.section(PromptSectionKey.rules),
    ]
    user_parts = [
        f"## Mission\n{bundle.section(PromptSectionKey.mission)}",
        f"## Grammar\n{bundle.section(PromptSectionKey.grammar)}",
        f"## Vocabulary\n{bundle.section(PromptSectionKey.vocabulary)}",
        f"## Output Format\n{bundle.section(PromptSectionKey.output_format)}",
        f"## Constraints\n{bundle.section(PromptSectionKey.constraints)}",
        f"## Success Criteria\n{bundle.section(PromptSectionKey.success_criteria)}",
        _JSON_OUTPUT_SCHEMA.strip(),
    ]
    system = "\n\n".join(part for part in system_parts if part.strip())
    user = "\n\n".join(part for part in user_parts if part.strip())
    return system, user
