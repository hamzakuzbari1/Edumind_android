"""Legacy ID map tables (G0/G1) — read adapters only; catalog owns topic authority."""

from __future__ import annotations

from app.services.language_grammar.enums import GrammarLegacyIdKind
from app.services.language_grammar.id_canon import is_canonical_grammar_id, normalize_grammar_id

# Speaking gram_* IDs that must exist in the shared Grammar Catalog (migration contract).
# The catalog is the authority; this set is a compatibility checklist, not a second catalog.
SPEAKING_GRAM_IDS: frozenset[str] = frozenset(
    {
        "gram_present_simple",
        "gram_basic_questions",
        "gram_past_simple",
        "gram_connectors_and_but",
        "gram_going_to",
        "gram_present_perfect",
        "gram_first_conditional",
        "gram_reported_speech_light",
        "gram_mixed_conditionals_light",
        "gram_passive_voice",
        "gram_relative_clauses",
        "gram_advanced_modals",
        "gram_cleft_emphasis",
        "gram_concession",
    }
)

# Writing structure_id → grammar_id (expand as Writing migrates to shared IDs).
WRITING_STRUCTURE_TO_GRAMMAR_ID: dict[str, str] = {
    "present_simple": "gram_present_simple",
    "structure_present_simple": "gram_present_simple",
    "past_simple": "gram_past_simple",
    "structure_past_simple": "gram_past_simple",
    "present_perfect": "gram_present_perfect",
    "structure_present_perfect": "gram_present_perfect",
    "first_conditional": "gram_first_conditional",
    "structure_first_conditional": "gram_first_conditional",
    "passive_voice": "gram_passive_voice",
    "structure_passive_voice": "gram_passive_voice",
    "basic_questions": "gram_basic_questions",
    "structure_basic_questions": "gram_basic_questions",
    "connectors_and_but": "gram_connectors_and_but",
    "going_to": "gram_going_to",
    "reported_speech": "gram_reported_speech_light",
    "relative_clauses": "gram_relative_clauses",
}

# BKT KnowledgeComponent codes → grammar_id (deprecate as source of truth after cutover).
BKT_GRAMMAR_TO_GRAMMAR_ID: dict[str, str] = {
    "grammar.present_simple": "gram_present_simple",
    "grammar.past_tenses": "gram_past_simple",
    "grammar.present_perfect": "gram_present_perfect",
    "grammar.conditionals": "gram_first_conditional",
}


def resolve_speaking_gram_id(legacy_id: str) -> str | None:
    """Map speaking gram_* → grammar_id (identity when already canonical)."""
    normalized = normalize_grammar_id(legacy_id)
    if is_canonical_grammar_id(normalized) and (
        normalized in SPEAKING_GRAM_IDS or normalized.startswith("gram_")
    ):
        return normalized
    return None


def resolve_writing_structure_id(structure_id: str) -> str | None:
    """Map Writing structure_id → grammar_id."""
    raw = (structure_id or "").strip()
    if not raw:
        return None
    if is_canonical_grammar_id(normalize_grammar_id(raw)):
        return normalize_grammar_id(raw)
    key = raw.lower()
    return WRITING_STRUCTURE_TO_GRAMMAR_ID.get(key)


def resolve_bkt_grammar_code(code: str) -> str | None:
    """Map BKT grammar.* KC code → grammar_id."""
    key = (code or "").strip().lower()
    if not key:
        return None
    return BKT_GRAMMAR_TO_GRAMMAR_ID.get(key)


def resolve_legacy_grammar_id(
    legacy_id: str,
    *,
    kind: GrammarLegacyIdKind,
) -> str | None:
    """Resolve a legacy identifier into canonical grammar_id."""
    if kind is GrammarLegacyIdKind.speaking_gram:
        return resolve_speaking_gram_id(legacy_id)
    if kind is GrammarLegacyIdKind.writing_structure:
        return resolve_writing_structure_id(legacy_id)
    if kind is GrammarLegacyIdKind.bkt_grammar:
        return resolve_bkt_grammar_code(legacy_id)
    return None
