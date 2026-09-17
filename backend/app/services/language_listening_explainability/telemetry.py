"""Explainability telemetry (Phase 3.4)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from app.services.language_listening_explainability.builder import EXPECTED_SIGNALS
from app.services.language_listening_explainability.types import ExplainabilitySignals, ExplainabilityTelemetry

T = TypeVar("T")


def measure_explainability(
    fn: Callable[[], T],
    signals: ExplainabilitySignals,
) -> tuple[T, ExplainabilityTelemetry]:
    start = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    present = set(signals.present_keys)
    missing = tuple(k for k in EXPECTED_SIGNALS if k not in present)
    used = tuple(k for k in EXPECTED_SIGNALS if k in present)
    completeness = len(used) / max(1, len(EXPECTED_SIGNALS))

    telemetry = ExplainabilityTelemetry(
        generation_time_ms=elapsed_ms,
        signals_used=used,
        missing_signals=missing,
        coverage_completeness=completeness,
    )
    return result, telemetry
