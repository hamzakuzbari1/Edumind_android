"""Types for Grammar Legacy Bridge (G0)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_grammar.enums import GrammarLegacyIdKind
from app.services.language_grammar_legacy_bridge.maps import resolve_legacy_grammar_id


@dataclass(frozen=True, slots=True)
class GrammarLegacyMapping:
    """Documented legacy → canonical mapping result."""

    kind: GrammarLegacyIdKind
    legacy_id: str
    grammar_id: str | None


def map_legacy_id(kind: GrammarLegacyIdKind, legacy_id: str) -> GrammarLegacyMapping:
    """Pure read adapter — never invents educational decisions."""
    return GrammarLegacyMapping(
        kind=kind,
        legacy_id=legacy_id,
        grammar_id=resolve_legacy_grammar_id(legacy_id, kind=kind),
    )
