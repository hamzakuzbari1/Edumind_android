"""Diversity statistics for listening intelligence (Phase 2.2)."""

from __future__ import annotations

from collections import Counter

from app.services.language_listening_intelligence.memory import situation_on_cooldown
from app.services.language_listening_intelligence.types import (
    ListeningDiversityStats,
    ListeningHistoryEntry,
)

DEFAULT_SITUATION_COOLDOWN = 5


def compute_diversity_stats(
    history: list[ListeningHistoryEntry],
    *,
    situation_cooldown: int = DEFAULT_SITUATION_COOLDOWN,
) -> ListeningDiversityStats:
    stats = ListeningDiversityStats(total_generations=len(history))
    if not history:
        stats.diversity_score = 100.0
        return stats

    situation_counts = Counter(h.situation for h in history)
    category_counts = Counter(h.category for h in history if h.category)
    format_counts = Counter(h.narrative_format for h in history if h.narrative_format)
    difficulty_counts = Counter(h.difficulty_band for h in history if h.difficulty_band)

    stats.situation_counts = dict(situation_counts)
    stats.category_counts = dict(category_counts)
    stats.format_counts = dict(format_counts)
    stats.difficulty_counts = dict(difficulty_counts)

    sorted_situations = situation_counts.most_common()
    stats.most_used_situations = sorted_situations[:5]
    stats.least_used_situations = sorted(situation_counts.items(), key=lambda x: x[1])[:5]

    if situation_counts:
        stats.average_repetitions = sum(situation_counts.values()) / len(situation_counts)

    # Consecutive same situation
    max_run = 1
    run = 1
    for idx in range(1, len(history)):
        if history[idx].situation == history[idx - 1].situation:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    stats.max_consecutive_same_situation = max_run if len(history) > 1 else (1 if history else 0)

    # Cooldown violations
    violations = 0
    for idx in range(len(history)):
        situation = history[idx].situation
        prior = history[:idx]
        if situation_on_cooldown(situation, prior, situation_cooldown):
            violations += 1
    stats.cooldown_violations = violations

    # Diversity score 0–100
    unique_situations = len(situation_counts)
    unique_categories = len(category_counts)
    unique_formats = len(format_counts)
    total = len(history)

    situation_entropy = unique_situations / max(1, min(total, 18))
    category_balance = 1.0
    if category_counts:
        max_cat_share = max(category_counts.values()) / total
        category_balance = max(0.0, 1.0 - max(0.0, max_cat_share - (1 / max(1, len(category_counts))) * 2))

    cooldown_penalty = min(40, violations * 4)
    consecutive_penalty = min(20, max(0, max_run - 1) * 10)

    raw = (
        situation_entropy * 30
        + category_balance * 30
        + (unique_formats / max(1, min(total, 9))) * 20
        + max(0, 20 - cooldown_penalty - consecutive_penalty)
    )
    stats.diversity_score = round(min(100.0, max(0.0, raw)), 1)
    return stats
