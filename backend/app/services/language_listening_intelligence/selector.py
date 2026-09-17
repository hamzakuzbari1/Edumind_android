"""Weighted selection engine for next listening lesson (Phase 2.2)."""

from __future__ import annotations

import hashlib

from app.services.language_cefr.engine import normalize_cefr_level
from app.services.language_listening_intelligence.categories import (
    category_for_situation,
    interest_category_weights,
    narrative_format_for,
)
from app.services.language_listening_intelligence.memory import (
    recent_categories,
    recent_difficulties,
    recent_formats,
    situation_on_cooldown,
)
from app.services.language_listening_intelligence.types import (
    DifficultyBand,
    ListeningCategory,
    ListeningHistoryEntry,
    ListeningIntelligencePlan,
)
from app.services.language_listening_quality.catalog import (
    FORMAT_BY_SITUATION,
    LISTENING_QUESTION_EMPHASIS_BY_LEVEL,
    NARRATIVE_ARCS,
    OPENING_STYLES,
    PACE_HINTS,
    SITUATION_BRIEFS,
    SITUATIONS_BY_LEVEL,
    SPEAKER_COUNT_BY_FORMAT,
)
from app.services.language_listening_quality.types import (
    EndingStyle,
    ListeningQualitySpec,
    ListeningSituationKind,
    NarrativeArc,
    OpeningStyle,
    PaceHint,
    TranscriptFormatHint,
)

SITUATION_COOLDOWN = 5
FORMAT_COOLDOWN = 3
CATEGORY_WINDOW = 12
INTEREST_WEIGHT_FACTOR = 1.0
CATEGORY_BALANCE_FACTOR = 2.4
FORMAT_BALANCE_FACTOR = 1.6
STALE_SITUATION_BOOST = 1.8

_DIFFICULTY_CYCLE = (DifficultyBand.easy, DifficultyBand.normal, DifficultyBand.challenging)
_ENDING_STYLES: tuple[EndingStyle, ...] = tuple(EndingStyle)


def _deterministic_index(key: str, modulo: int) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % modulo


def _pick_difficulty(history: list[ListeningHistoryEntry], level: str, situation: str) -> DifficultyBand:
    recent = recent_difficulties(history, 6)
    if not recent:
        return DifficultyBand.normal
    last = recent[-1]
    try:
        idx = _DIFFICULTY_CYCLE.index(DifficultyBand(last))
        return _DIFFICULTY_CYCLE[(idx + 1) % len(_DIFFICULTY_CYCLE)]
    except ValueError:
        return DifficultyBand.normal


def _pick_variant(
    options: tuple,
    *,
    level: str,
    situation: str,
    field: str,
    generation_index: int,
) -> object:
    key = f"{level}|{situation}|{field}|{generation_index}"
    return options[_deterministic_index(key, len(options))]


def _category_weight(category: str, recent: list[str]) -> float:
    if not recent:
        return 1.0
    counts: dict[str, int] = {}
    for cat in recent:
        counts[cat] = counts.get(cat, 0) + 1
    avg = sum(counts.values()) / max(1, len(counts))
    deficit = avg - counts.get(category, 0)
    return max(0.35, 1.0 + deficit * 0.25 * CATEGORY_BALANCE_FACTOR)


def _format_weight(nfmt: str, recent: list[str]) -> float:
    if not recent:
        return 1.0
    if nfmt in recent[-FORMAT_COOLDOWN:]:
        return 0.05
    count = recent.count(nfmt)
    return max(0.4, 1.0 + (recent.count(nfmt) * -0.15) + FORMAT_BALANCE_FACTOR * (0.5 - count / max(1, len(recent))))


def _situation_staleness_boost(situation: str, history: list[ListeningHistoryEntry]) -> float:
    if not history:
        return 1.0
    for idx in range(len(history) - 1, -1, -1):
        if history[idx].situation == situation:
            distance = len(history) - idx
            return min(STALE_SITUATION_BOOST, 1.0 + distance * 0.08)
    return STALE_SITUATION_BOOST


def _build_quality_spec(
    *,
    level: str,
    situation: ListeningSituationKind,
    format_hint: TranscriptFormatHint,
    speaker_count: int,
    narrative_arc: NarrativeArc,
    opening_style: OpeningStyle,
    ending_style: EndingStyle,
    pace: PaceHint,
) -> ListeningQualitySpec:
    from app.services.language_listening_quality.catalog import OVERUSED_TOPIC_HINTS

    question_emphasis = LISTENING_QUESTION_EMPHASIS_BY_LEVEL.get(level, LISTENING_QUESTION_EMPHASIS_BY_LEVEL["B1"])
    return ListeningQualitySpec(
        level=level,
        situation=situation,
        situation_brief=SITUATION_BRIEFS[situation],
        format_hint=format_hint,
        speaker_count=speaker_count,
        narrative_arc=narrative_arc,
        opening_style=opening_style,
        ending_style=ending_style,
        pace=pace,
        avoid_topics=OVERUSED_TOPIC_HINTS,
        listening_question_emphasis=question_emphasis,
    )


def select_next_listening_plan(
    level: str,
    history: list[ListeningHistoryEntry],
    *,
    themes: str = "",
    topics: str = "",
    generation_index: int | None = None,
) -> ListeningIntelligencePlan:
    """Choose the next listening lesson using weighted intelligence (not random-only)."""
    norm_level = normalize_cefr_level(level)
    gen_idx = generation_index if generation_index is not None else len(history)

    pool = SITUATIONS_BY_LEVEL.get(norm_level, SITUATIONS_BY_LEVEL["B1"])
    interest_weights = interest_category_weights(topics, themes=themes)
    recent_cats = recent_categories(history, CATEGORY_WINDOW)
    recent_fmts = recent_formats(history, CATEGORY_WINDOW)

    candidates: list[tuple[float, ListeningIntelligencePlan, str]] = []

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

        format_pool = FORMAT_BY_SITUATION.get(situation, (TranscriptFormatHint.monologue,))
        for format_hint in format_pool:
            narrative_arc: NarrativeArc = _pick_variant(  # type: ignore[assignment]
                NARRATIVE_ARCS,
                level=norm_level,
                situation=situation.value,
                field="arc",
                generation_index=gen_idx,
            )
            opening_style: OpeningStyle = _pick_variant(  # type: ignore[assignment]
                OPENING_STYLES,
                level=norm_level,
                situation=situation.value,
                field="opening",
                generation_index=gen_idx,
            )
            ending_style: EndingStyle = _pick_variant(  # type: ignore[assignment]
                _ENDING_STYLES,
                level=norm_level,
                situation=situation.value,
                field="ending",
                generation_index=gen_idx,
            )
            pace: PaceHint = _pick_variant(  # type: ignore[assignment]
                PACE_HINTS,
                level=norm_level,
                situation=situation.value,
                field="pace",
                generation_index=gen_idx,
            )
            speaker_pool = SPEAKER_COUNT_BY_FORMAT.get(format_hint, (1,))
            speaker_count: int = _pick_variant(  # type: ignore[assignment]
                speaker_pool,
                level=norm_level,
                situation=situation.value,
                field="speakers",
                generation_index=gen_idx,
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
                from app.services.language_listening_intelligence.types import NarrativeFormat

                narrative_format = NarrativeFormat(nfmt)
            except ValueError:
                from app.services.language_listening_intelligence.types import NarrativeFormat

                narrative_format = NarrativeFormat.monologue

            plan = ListeningIntelligencePlan(
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
                selection_reason=(
                    f"category_balance={cat_weight:.2f}, interest={interest_boost:.2f}, "
                    f"staleness={stale_boost:.2f}, format={fmt_weight:.2f}"
                ),
            )
            candidates.append((score, plan, nfmt))

    if not candidates:
        # Cooldown exhausted all situations — pick least recently used
        usage: dict[str, int] = {}
        for h in history:
            usage[h.situation] = usage.get(h.situation, 0) + 1
        fallback_situation = min(pool, key=lambda s: (usage.get(s.value, 0), s.value))
        format_hint = FORMAT_BY_SITUATION.get(fallback_situation, (TranscriptFormatHint.monologue,))[0]
        narrative_arc = NarrativeArc.setup_development_resolution
        opening_style = OpeningStyle.contextual_preview
        ending_style = EndingStyle.summary_sign_off
        pace = PaceHint.conversational
        speaker_count = SPEAKER_COUNT_BY_FORMAT.get(format_hint, (1,))[0]
        category = category_for_situation(fallback_situation)
        difficulty = _pick_difficulty(history, norm_level, fallback_situation.value)
        quality_spec = _build_quality_spec(
            level=norm_level,
            situation=fallback_situation,
            format_hint=format_hint,
            speaker_count=speaker_count,
            narrative_arc=narrative_arc,
            opening_style=opening_style,
            ending_style=ending_style,
            pace=pace,
        )
        from app.services.language_listening_intelligence.types import NarrativeFormat

        nfmt = narrative_format_for(fallback_situation, format_hint, narrative_arc.value)
        return ListeningIntelligencePlan(
            level=norm_level,
            situation=fallback_situation,
            category=category,
            format_hint=format_hint,
            narrative_format=NarrativeFormat(nfmt),
            difficulty_band=difficulty,
            narrative_arc=narrative_arc,
            opening_style=opening_style,
            ending_style=ending_style.value,
            pace=pace,
            speaker_count=speaker_count,
            quality_spec=quality_spec,
            selection_score=0.01,
            selection_reason="fallback_least_used_situation",
        )

    candidates.sort(key=lambda item: (-item[0], item[2], item[1].situation.value))
    best_score, best_plan, _ = candidates[0]
    return ListeningIntelligencePlan(
        level=best_plan.level,
        situation=best_plan.situation,
        category=best_plan.category,
        format_hint=best_plan.format_hint,
        narrative_format=best_plan.narrative_format,
        difficulty_band=best_plan.difficulty_band,
        narrative_arc=best_plan.narrative_arc,
        opening_style=best_plan.opening_style,
        ending_style=best_plan.ending_style,
        pace=best_plan.pace,
        speaker_count=best_plan.speaker_count,
        quality_spec=best_plan.quality_spec,
        selection_score=best_score,
        selection_reason=best_plan.selection_reason,
    )
