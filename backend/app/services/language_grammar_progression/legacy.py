"""Legacy ID normalization for Progression student snapshot (read-only maps)."""

from __future__ import annotations

from app.services.language_grammar.enums import GrammarLegacyIdKind
from app.services.language_grammar.id_canon import is_canonical_grammar_id, normalize_grammar_id
from app.services.language_grammar_legacy_bridge.maps import resolve_legacy_grammar_id


def normalize_to_grammar_id(raw: str) -> str | None:
    """Map canonical or legacy identifiers into grammar_id (None if unresolved)."""
    text = (raw or "").strip()
    if not text:
        return None
    normalized = normalize_grammar_id(text)
    if is_canonical_grammar_id(normalized):
        return normalized
    for kind in (
        GrammarLegacyIdKind.speaking_gram,
        GrammarLegacyIdKind.writing_structure,
        GrammarLegacyIdKind.bkt_grammar,
    ):
        resolved = resolve_legacy_grammar_id(text, kind=kind)
        if resolved:
            return resolved
    return None


def normalize_id_set(raw_ids: frozenset[str] | set[str] | tuple[str, ...]) -> frozenset[str]:
    out: set[str] = set()
    for raw in raw_ids:
        gid = normalize_to_grammar_id(str(raw))
        if gid:
            out.add(gid)
    return frozenset(out)
