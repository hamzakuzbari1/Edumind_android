"""Category mapping and interest inference (Phase 2.2)."""

from __future__ import annotations

import re

from app.services.language_listening_intelligence.types import ListeningCategory
from app.services.language_listening_quality.types import (
    ListeningSituationKind,
    TranscriptFormatHint,
)

SITUATION_CATEGORY: dict[ListeningSituationKind, ListeningCategory] = {
    ListeningSituationKind.airport: ListeningCategory.travel,
    ListeningSituationKind.travel: ListeningCategory.travel,
    ListeningSituationKind.hotel: ListeningCategory.travel,
    ListeningSituationKind.restaurant: ListeningCategory.daily_life,
    ListeningSituationKind.shopping: ListeningCategory.daily_life,
    ListeningSituationKind.phone_call: ListeningCategory.daily_life,
    ListeningSituationKind.doctor: ListeningCategory.health,
    ListeningSituationKind.school: ListeningCategory.education,
    ListeningSituationKind.lecture: ListeningCategory.education,
    ListeningSituationKind.office: ListeningCategory.business,
    ListeningSituationKind.meeting: ListeningCategory.business,
    ListeningSituationKind.interview: ListeningCategory.entertainment,
    ListeningSituationKind.podcast: ListeningCategory.entertainment,
    ListeningSituationKind.radio: ListeningCategory.entertainment,
    ListeningSituationKind.museum: ListeningCategory.culture,
    ListeningSituationKind.news: ListeningCategory.news,
    ListeningSituationKind.public_announcement: ListeningCategory.public_services,
    ListeningSituationKind.customer_support: ListeningCategory.customer_service,
}

INTEREST_CATEGORY_BOOSTS: dict[str, tuple[ListeningCategory, float]] = {
    "programming": (ListeningCategory.technology, 0.18),
    "coding": (ListeningCategory.technology, 0.18),
    "software": (ListeningCategory.technology, 0.16),
    "computer": (ListeningCategory.technology, 0.14),
    "technology": (ListeningCategory.technology, 0.16),
    "tech": (ListeningCategory.technology, 0.14),
    "football": (ListeningCategory.entertainment, 0.12),
    "soccer": (ListeningCategory.entertainment, 0.12),
    "sport": (ListeningCategory.entertainment, 0.10),
    "sports": (ListeningCategory.entertainment, 0.10),
    "music": (ListeningCategory.entertainment, 0.10),
    "travel": (ListeningCategory.travel, 0.12),
    "health": (ListeningCategory.health, 0.12),
    "medicine": (ListeningCategory.health, 0.12),
    "business": (ListeningCategory.business, 0.12),
    "environment": (ListeningCategory.environment, 0.14),
    "climate": (ListeningCategory.environment, 0.14),
    "news": (ListeningCategory.news, 0.10),
    "culture": (ListeningCategory.culture, 0.10),
    "museum": (ListeningCategory.culture, 0.10),
}

MAX_INTEREST_BOOST = 0.22


def category_for_situation(situation: ListeningSituationKind) -> ListeningCategory:
    return SITUATION_CATEGORY.get(situation, ListeningCategory.daily_life)


def interest_category_weights(topics: str, *, themes: str = "") -> dict[ListeningCategory, float]:
    """Parse learner interests; capped boost to avoid overfitting."""
    blob = f"{topics} {themes}".lower()
    tokens = set(re.findall(r"[a-z]{3,}", blob))
    weights: dict[ListeningCategory, float] = {}
    for keyword, (category, boost) in INTEREST_CATEGORY_BOOSTS.items():
        if keyword in tokens or keyword in blob:
            weights[category] = min(MAX_INTEREST_BOOST, weights.get(category, 0.0) + boost)
    return weights


def narrative_format_for(
    situation: ListeningSituationKind,
    format_hint: TranscriptFormatHint,
    narrative_arc: str,
) -> str:
    from app.services.language_listening_intelligence.types import NarrativeFormat

    if situation == ListeningSituationKind.public_announcement:
        return NarrativeFormat.announcement.value
    if situation == ListeningSituationKind.podcast:
        return NarrativeFormat.podcast.value
    if situation == ListeningSituationKind.news:
        return NarrativeFormat.news.value
    if format_hint == TranscriptFormatHint.panel:
        return NarrativeFormat.panel.value
    if format_hint == TranscriptFormatHint.interview:
        return NarrativeFormat.interview.value
    if format_hint == TranscriptFormatHint.lecture:
        return NarrativeFormat.lecture.value
    if format_hint == TranscriptFormatHint.dialogue:
        return NarrativeFormat.dialogue.value
    if format_hint == TranscriptFormatHint.discussion:
        return NarrativeFormat.discussion.value
    if narrative_arc == "journey_with_complication":
        return NarrativeFormat.story.value
    return NarrativeFormat.monologue.value
