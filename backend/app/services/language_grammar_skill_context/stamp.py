"""Stamp / extract grammar_id on skill activity bodies (Wave C)."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from app.services.language_grammar_skill_context.types import SkillGrammarContext


STAMP_KEY = "grammar_id"


def stamp_body(body: MutableMapping[str, Any] | dict[str, Any], ctx: SkillGrammarContext) -> dict[str, Any]:
    """Merge authoritative grammar stamp into a skill body dict."""
    out = dict(body)
    out.update(ctx.as_stamp_dict())
    return out


def stamp_constraints_payload(
    payload: MutableMapping[str, Any] | dict[str, Any],
    ctx: SkillGrammarContext,
) -> dict[str, Any]:
    """Stamp speaking/writing-style constraint payloads with resolver grammar."""
    out = dict(payload)
    out["grammar_id"] = ctx.grammar_id
    out["display_code"] = ctx.display_code
    # Keep list fields aligned with resolver authority (primary first).
    topic_ids = [ctx.grammar_id, *list(ctx.secondary_grammar_ids)]
    out["grammar_topic_ids"] = topic_ids
    out["grammar_targets"] = list(ctx.grammar_targets) or [ctx.display_name]
    out["grammar_prompt_block"] = ctx.prompt_block()
    return out


def extract_stamped_grammar_id(payload: Mapping[str, Any] | None) -> str | None:
    """Read stamped grammar_id from a stored body/constraints payload."""
    if not payload:
        return None
    raw = payload.get(STAMP_KEY) or payload.get("grammar_target")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().lower()
    ids = payload.get("grammar_topic_ids")
    if isinstance(ids, (list, tuple)) and ids:
        first = str(ids[0] or "").strip().lower()
        return first or None
    return None


def merge_prompt_context(adaptive_context: str, ctx: SkillGrammarContext | None) -> str:
    """Prepend shared grammar prompt block to an existing adaptive context string."""
    if ctx is None:
        return adaptive_context or ""
    block = ctx.prompt_block()
    base = (adaptive_context or "").strip()
    if not base:
        return block
    if ctx.grammar_id in base and "GRAMMAR TARGET" in base:
        return base
    return f"{block}\n\n{base}"
