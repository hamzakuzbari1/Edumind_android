"""CEFR band ordering helpers for Grammar Catalog (G1)."""

from __future__ import annotations

from app.services.language_grammar.enums import GrammarCEFRBand

CEFR_RANK: dict[GrammarCEFRBand, int] = {
    GrammarCEFRBand.A1: 1,
    GrammarCEFRBand.A2: 2,
    GrammarCEFRBand.B1: 3,
    GrammarCEFRBand.B2: 4,
    GrammarCEFRBand.C1: 5,
    GrammarCEFRBand.C2: 6,
}

CEFR_SEQUENCE: tuple[GrammarCEFRBand, ...] = (
    GrammarCEFRBand.A1,
    GrammarCEFRBand.A2,
    GrammarCEFRBand.B1,
    GrammarCEFRBand.B2,
    GrammarCEFRBand.C1,
    GrammarCEFRBand.C2,
)


def cefr_rank(band: GrammarCEFRBand) -> int:
    return CEFR_RANK[band]


def cefr_at_most(band: GrammarCEFRBand, limit: GrammarCEFRBand) -> bool:
    return cefr_rank(band) <= cefr_rank(limit)
