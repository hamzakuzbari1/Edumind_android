"""Speaking grammar projection — reads shared Grammar Catalog (G1 authority).

This module no longer owns topic definitions. It projects catalog topics into
Speaking ``GrammarTarget`` shapes for Educational Cases until full Integration (G3).
"""

from __future__ import annotations

from app.services.language_grammar.enums import GrammarCEFRBand
from app.services.language_grammar_catalog.catalog import get_topic, topics_for_cefr
from app.services.language_speaking_curriculum_engine.types import GrammarTarget

# Legacy Speaking CEFR packs — IDs must exist in the shared catalog.
_SPEAKING_PACK_IDS: dict[str, tuple[str, ...]] = {
    "A1": ("gram_present_simple", "gram_basic_questions"),
    "A2": ("gram_past_simple", "gram_connectors_and_but", "gram_going_to"),
    "B1": ("gram_present_perfect", "gram_first_conditional", "gram_reported_speech_light"),
    "B2": ("gram_mixed_conditionals_light", "gram_passive_voice", "gram_relative_clauses"),
    "C1": ("gram_advanced_modals", "gram_cleft_emphasis", "gram_concession"),
    "C2": ("gram_nominalisation", "gram_hedging_stance", "gram_discourse_signalling"),
}


def _to_target(grammar_id: str) -> GrammarTarget:
    topic = get_topic(grammar_id)
    if topic is None:
        raise KeyError(f"Speaking grammar pack references unknown catalog id: {grammar_id}")
    return GrammarTarget(
        grammar_topic_id=topic.grammar_id,
        label=topic.display_name,
        cefr_suitability=topic.cefr_band.value,
        focus_note=topic.focus_note,
        demonstration_forms=topic.demonstration_patterns,
    )


def _normalize_pack_key(level: str) -> str:
    key = (level or "A2").upper()
    if key in _SPEAKING_PACK_IDS:
        return key
    try:
        band = GrammarCEFRBand(key)
    except ValueError:
        return "A2"
    # Nearest defined pack at or below the requested band.
    order = ["A1", "A2", "B1", "B2", "C1", "C2"]
    idx = order.index(band.value)
    for candidate in reversed(order[: idx + 1]):
        if candidate in _SPEAKING_PACK_IDS:
            return candidate
    return "A2"


def _pack_for_cefr(level: str) -> tuple[GrammarTarget, ...]:
    key = _normalize_pack_key(level)
    return tuple(_to_target(gid) for gid in _SPEAKING_PACK_IDS[key])


# Public names preserved for existing Speaking imports.
GRAMMAR_A1: tuple[GrammarTarget, ...] = _pack_for_cefr("A1")
GRAMMAR_A2: tuple[GrammarTarget, ...] = _pack_for_cefr("A2")
GRAMMAR_B1: tuple[GrammarTarget, ...] = _pack_for_cefr("B1")
GRAMMAR_B2: tuple[GrammarTarget, ...] = _pack_for_cefr("B2")
GRAMMAR_C1: tuple[GrammarTarget, ...] = _pack_for_cefr("C1")


def select_grammar_targets(*, cefr: str, count: int) -> list[GrammarTarget]:
    """Legacy helper for catalog projection tests ONLY.

    Wave D P0-3: Speaking product paths must NOT call this. Grammar targets come
    exclusively from language_grammar_target_resolver / SkillGrammarContext.
    ``enrich_speaking_constraints_payload`` no longer invokes this function.
    """
    level = (cefr or "A2").upper()
    pack_ids = _SPEAKING_PACK_IDS.get(_normalize_pack_key(level))
    if pack_ids:
        targets = [_to_target(gid) for gid in pack_ids]
    else:
        try:
            band = GrammarCEFRBand(level)
        except ValueError:
            band = GrammarCEFRBand.A2
        targets = [
            GrammarTarget(
                grammar_topic_id=t.grammar_id,
                label=t.display_name,
                cefr_suitability=t.cefr_band.value,
                focus_note=t.focus_note,
                demonstration_forms=t.demonstration_patterns,
            )
            for t in topics_for_cefr(band)
        ]
    n = max(1, int(count or 1))
    return list(targets[:n])
