"""Stability policy thresholds (Phase 5.3.1).

All stability rules live here — never hardcode thresholds in the engine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StabilityPolicy:
    rolling_window: int = 10
    min_rolling_average: float = 90.0
    min_rolling_minimum: float = 85.0
    gate_pass_recent_lessons: int = 3
    severe_confidence_regression: float = 0.08
    severe_evidence_regression: float = 0.08
    stable_lesson_threshold: float = 85.0
    min_lessons_for_high_confidence: int = 5
    max_history_entries: int = 24

    # Promotion confidence component weights (sum = 1.0).
    weight_stability: float = 0.35
    weight_smoothed_readiness: float = 0.25
    weight_gate_consistency: float = 0.15
    weight_trends: float = 0.15
    weight_challenge: float = 0.10

    # Single-lesson spike cap — one excellent lesson cannot unlock high confidence.
    single_lesson_confidence_cap: float = 55.0
    short_history_confidence_cap: float = 72.0


DEFAULT_STABILITY_POLICY = StabilityPolicy()
