"""Enumerate intelligence candidates for curriculum scoring (Phase 2.3)."""

from __future__ import annotations

from app.services.language_cefr.engine import normalize_cefr_level
from app.services.language_listening_intelligence.categories import (
    category_for_situation,
    interest_category_weights,
    narrative_format_for,
)
from app.services.language_listening_intelligence.memory import (
    recent_categories,
    recent_formats,
    situation_on_cooldown,
)
from app.services.language_listening_intelligence.selector import (
    CATEGORY_WINDOW,
    FORMAT_BALANCE_FACTOR,
    INTEREST_WEIGHT_FACTOR,
    SITUATION_COOLDOWN,
    _build_quality_spec,
    _category_weight,
    _format_weight,
    _pick_difficulty,
    _pick_variant,
    _situation_staleness_boost,
)
from app.services.language_listening_intelligence.types import (
    ListeningCategory,
    ListeningHistoryEntry,
    ListeningIntelligencePlan,
    NarrativeFormat,
)
from app.services.language_listening_quality.catalog import (
    FORMAT_BY_SITUATION,
    NARRATIVE_ARCS,
    OPENING_STYLES,
    PACE_HINTS,
    SITUATIONS_BY_LEVEL,
    SPEAKER_COUNT_BY_FORMAT,
)
from app.services.language_listening_quality.types import EndingStyle, NarrativeArc, OpeningStyle, PaceHint, TranscriptFormatHint

_ENDING_STYLES: tuple[EndingStyle, ...] = tuple(EndingStyle)


def enumerate_intelligence_candidates(
    level: str,
    history: list[ListeningHistoryEntry],
    *,
    themes: str = "",
    topics: str = "",
    generation_index: int,
) -> list[ListeningIntelligencePlan]:
    """Build all non-cooldown intelligence candidates (read-only use of Phase 2.2 helpers)."""
    norm_level = normalize_cefr_level(level)
    pool = SITUATIONS_BY_LEVEL.get(norm_level, SITUATIONS_BY_LEVEL["B1"])
    interest_weights = interest_category_weights(topics, themes=themes)
    recent_cats = recent_categories(history, CATEGORY_WINDOW)
    recent_fmts = recent_formats(history, CATEGORY_WINDOW)
    candidates: list[ListeningIntelligencePlan] = []

    for situation in pool:
        if situation_on_cooldown(situation.value, history, SITUATION_COOLDOWN):
            continue

        category = category_for_situation(situation)
        cat_weight = _category_weight(category.value, recent_cats)
        interest_boost = 1.0 + interest_weights.get(category, 0.0) * INTEREST_WEIGHT_FACTOR
        tech_boost = interest_weights.get(ListeningCategory.technology, 0.0)
        if tech_boost and situation.value in {"office", "meeting", "podcast", "news", "customer_support"}:
            interest_boost += tech_boost * 0.45
        stale_boost = _situation_staleness_boost(situation.value, history)
        base = cat_weight * interest_boost * stale_boost

        for format_hint in FORMAT_BY_SITUATION.get(situation, (TranscriptFormatHint.monologue,)):
            narrative_arc: NarrativeArc = _pick_variant(  # type: ignore[assignment]
                NARRATIVE_ARCS,
                level=norm_level,
                situation=situation.value,
                field="arc",
                generation_index=generation_index,
            )
            opening_style: OpeningStyle = _pick_variant(  # type: ignore[assignment]
                OPENING_STYLES,
                level=norm_level,
                situation=situation.value,
                field="opening",
                generation_index=generation_index,
            )
            ending_style: EndingStyle = _pick_variant(  # type: ignore[assignment]
                _ENDING_STYLES,
                level=norm_level,
                situation=situation.value,
                field="ending",
                generation_index=generation_index,
            )
            pace: PaceHint = _pick_variant(  # type: ignore[assignment]
                PACE_HINTS,
                level=norm_level,
                situation=situation.value,
                field="pace",
                generation_index=generation_index,
            )
            speaker_pool = SPEAKER_COUNT_BY_FORMAT.get(format_hint, (1,))
            speaker_count: int = _pick_variant(  # type: ignore[assignment]
                speaker_pool,
                level=norm_level,
                situation=situation.value,
                field="speakers",
                generation_index=generation_index,
            )
            nfmt = narrative_format_for(situation, format_hint, narrative_arc.value)
            fmt_weight = _format_weight(nfmt, recent_fmts)
            score = base * fmt_weight
            difficulty = _pick_difficulty(history, norm_level, situation.value)
            quality_spec = _build_quality_spec(
                level=norm_level,
                situation=situation,
                format_hint=format_hint,
                speaker_count=speaker_count,
                narrative_arc=narrative_arc,
                opening_style=opening_style,
                ending_style=ending_style,
                pace=pace,
            )
            try:
                narrative_format = NarrativeFormat(nfmt)
            except ValueError:
                narrative_format = NarrativeFormat.monologue

            candidates.append(
                ListeningIntelligencePlan(
                    level=norm_level,
                    situation=situation,
                    category=category,
                    format_hint=format_hint,
                    narrative_format=narrative_format,
                    difficulty_band=difficulty,
                    narrative_arc=narrative_arc,
                    opening_style=opening_style,
                    ending_style=ending_style.value,
                    pace=pace,
                    speaker_count=speaker_count,
                    quality_spec=quality_spec,
                    selection_score=score,
                    selection_reason=f"intelligence_base={score:.2f}",
                )
            )
    return candidates
