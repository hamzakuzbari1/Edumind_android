"""Reject generator drift away from resolver grammar (Wave C)."""

from __future__ import annotations

from typing import Any, Mapping

from app.services.language_grammar.id_canon import normalize_grammar_id
from app.services.language_grammar_skill_context.stamp import extract_stamped_grammar_id
from app.services.language_grammar_skill_context.types import (
    SkillGrammarContext,
    SkillGrammarContextError,
)


def assert_grammar_id_matches(
    *,
    stamped: str | SkillGrammarContext | None,
    claimed: str | None,
    allow_missing_claim: bool = True,
) -> str:
    """Ensure claimed grammar_id equals resolver stamp.

    If ``claimed`` is empty and ``allow_missing_claim`` is True, returns the stamp.
    """
    if isinstance(stamped, SkillGrammarContext):
        expected = stamped.grammar_id
    else:
        expected = normalize_grammar_id(stamped or "")
    if not expected:
        raise SkillGrammarContextError(
            "missing_stamp",
            "No resolver grammar stamp is available for validation",
        )
    claim = normalize_grammar_id(claimed or "")
    if not claim:
        if allow_missing_claim:
            return expected
        raise SkillGrammarContextError(
            "missing_claim",
            "Generator did not declare grammar_id",
        )
    if claim != expected:
        raise SkillGrammarContextError(
            "grammar_mismatch",
            f"Generator claimed {claim!r} but resolver stamped {expected!r}",
        )
    return expected


def assert_payload_matches_stamp(
    payload: Mapping[str, Any] | None,
    *,
    stamped: str | SkillGrammarContext,
    allow_missing_claim: bool = True,
) -> str:
    """Validate a generated body/constraints dict against the resolver stamp."""
    claimed = extract_stamped_grammar_id(payload)
    # Prefer explicit drift fields if present and different from stamp key
    if payload:
        alt = payload.get("claimed_grammar_id") or payload.get("selected_grammar_id")
        if isinstance(alt, str) and alt.strip():
            claimed = alt.strip()
    return assert_grammar_id_matches(
        stamped=stamped,
        claimed=claimed,
        allow_missing_claim=allow_missing_claim,
    )
