"""Listening Promotion Test configuration (Phase 5.4).

Thresholds and structure defaults live here — not hardcoded in the engine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromotionTestConfig:
    assessment_count: int = 5
    pass_threshold: int = 80
    borderline_threshold: int = 65
    max_per_objective: int = 1
    session_ttl_seconds: int = 3600

    objective_pool: tuple[str, ...] = (
        "main_idea",
        "detail",
        "inference",
        "purpose",
        "speaker_intention",
        "opinion",
        "sequence",
        "prediction",
    )

    situation_pool: tuple[str, ...] = (
        "airport",
        "office",
        "phone_call",
        "announcements",
        "meeting",
        "radio",
        "hotel",
        "school",
    )

    format_pool: tuple[str, ...] = (
        "dialogue",
        "monologue",
        "announcement",
        "interview",
        "lecture_excerpt",
    )

    speaker_options: tuple[int, ...] = (1, 2, 3)


DEFAULT_PROMOTION_TEST_CONFIG = PromotionTestConfig()
