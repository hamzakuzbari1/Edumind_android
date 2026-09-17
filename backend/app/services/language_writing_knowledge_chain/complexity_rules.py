"""Context complexity validation rules (W1 refinement)."""

from __future__ import annotations

from app.services.language_writing.enums import ContextComplexity, OfficialWritingCEFR

# Recommended complexity ranges per Official CEFR (inclusive).
CEFR_COMPLEXITY_RANGES: dict[OfficialWritingCEFR, tuple[int, int]] = {
    OfficialWritingCEFR.A1: (1, 2),
    OfficialWritingCEFR.A2: (1, 3),
    OfficialWritingCEFR.B1: (2, 4),
    OfficialWritingCEFR.B2: (3, 5),
    OfficialWritingCEFR.C1: (4, 5),
    OfficialWritingCEFR.C2: (4, 5),
}


def complexity_range_for_cefr(cefr: OfficialWritingCEFR) -> tuple[int, int]:
    return CEFR_COMPLEXITY_RANGES[cefr]


def is_complexity_valid_for_cefr(*, cefr: OfficialWritingCEFR, complexity: ContextComplexity) -> bool:
    lo, hi = complexity_range_for_cefr(cefr)
    return lo <= int(complexity) <= hi


def complexity_validation_message(*, cefr: OfficialWritingCEFR, complexity: ContextComplexity) -> str | None:
    lo, hi = complexity_range_for_cefr(cefr)
    level = int(complexity)
    if level < lo:
        return f"complexity {level} below recommended minimum {lo} for {cefr.value}"
    if level > hi:
        return f"complexity {level} above recommended maximum {hi} for {cefr.value}"
    return None
