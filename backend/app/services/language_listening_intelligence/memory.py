"""Topic memory and history extraction (Phase 2.2)."""

from __future__ import annotations

from app.services.language_listening_intelligence.types import ListeningHistoryEntry

HISTORY_KEY = "listening_intelligence"


def history_entry_from_metadata(data: dict | None) -> ListeningHistoryEntry | None:
    if not isinstance(data, dict):
        return None
    situation = str(data.get("situation") or "").strip()
    if not situation:
        return None
    return ListeningHistoryEntry(
        situation=situation,
        category=str(data.get("category") or ""),
        format_hint=str(data.get("format_hint") or ""),
        narrative_format=str(data.get("narrative_format") or ""),
        difficulty_band=str(data.get("difficulty_band") or "normal"),
        narrative_arc=str(data.get("narrative_arc") or ""),
        level=str(data.get("level") or ""),
    )


def extract_history_from_bodies(bodies: list[dict]) -> list[ListeningHistoryEntry]:
    """Build chronological history (oldest first) from stored body_json dicts."""
    entries: list[ListeningHistoryEntry] = []
    for body in bodies:
        meta = body.get(HISTORY_KEY) if isinstance(body, dict) else None
        entry = history_entry_from_metadata(meta)
        if entry:
            entries.append(entry)
    return entries


def recent_situations(history: list[ListeningHistoryEntry], window: int) -> list[str]:
    if window <= 0 or not history:
        return []
    return [h.situation for h in history[-window:]]


def recent_categories(history: list[ListeningHistoryEntry], window: int) -> list[str]:
    if window <= 0 or not history:
        return []
    return [h.category for h in history[-window:] if h.category]


def recent_formats(history: list[ListeningHistoryEntry], window: int) -> list[str]:
    if window <= 0 or not history:
        return []
    return [h.narrative_format for h in history[-window:] if h.narrative_format]


def recent_difficulties(history: list[ListeningHistoryEntry], window: int) -> list[str]:
    if window <= 0 or not history:
        return []
    return [h.difficulty_band for h in history[-window:] if h.difficulty_band]


def situation_on_cooldown(
    situation: str,
    history: list[ListeningHistoryEntry],
    cooldown: int,
) -> bool:
    """True when situation appeared within the last ``cooldown`` generations."""
    if cooldown <= 0 or not history:
        return False
    recent = recent_situations(history, cooldown)
    return situation in recent
