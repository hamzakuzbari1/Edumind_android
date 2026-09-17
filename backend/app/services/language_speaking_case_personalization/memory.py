"""Educational Case memory ledger — avoid repeating identical experience worlds."""

from __future__ import annotations

from typing import Any

from app.services.language_speaking_case_personalization.types import CaseMemoryLedger

SPEAKING_CASE_MEMORY_KEY = "speaking_case_memory"


def case_memory_from_payload(payload: dict[str, Any] | None) -> CaseMemoryLedger:
    if not isinstance(payload, dict):
        return CaseMemoryLedger()
    raw = payload.get(SPEAKING_CASE_MEMORY_KEY)
    return CaseMemoryLedger.from_dict(raw if isinstance(raw, dict) else None)


def merge_case_memory_into_payload(
    payload: dict[str, Any] | None,
    ledger: CaseMemoryLedger,
) -> dict[str, Any]:
    out = dict(payload) if isinstance(payload, dict) else {}
    out[SPEAKING_CASE_MEMORY_KEY] = ledger.to_dict()
    return out


def _append_unique(seq: list[str], value: str, *, cap: int = 40) -> None:
    v = (value or "").strip()
    if not v:
        return
    cleaned = [x for x in seq if x != v]
    cleaned.append(v)
    seq[:] = cleaned[-cap:]


def record_completed_case(
    ledger: CaseMemoryLedger,
    *,
    title: str = "",
    setting: str = "",
    theme_key: str = "",
    case_category: str = "",
    case_archetype: str = "",
    emotional_theme: str = "",
    decision_pattern: str = "",
    stakeholders: list[str] | tuple[str, ...] | None = None,
    vocabulary_world: str = "",
) -> CaseMemoryLedger:
    """Update longitudinal memory after a frozen Educational Case is completed/generated."""
    _append_unique(ledger.used_case_titles, title)
    _append_unique(ledger.used_settings, setting)
    _append_unique(ledger.used_theme_keys, theme_key)
    _append_unique(ledger.used_categories, case_category)
    _append_unique(ledger.used_archetypes, case_archetype)
    _append_unique(ledger.used_emotional_themes, emotional_theme)
    _append_unique(ledger.used_decision_patterns, decision_pattern)
    _append_unique(ledger.used_vocabulary_worlds, vocabulary_world)
    if stakeholders:
        pattern = ", ".join(str(s) for s in stakeholders[:4] if str(s).strip())
        _append_unique(ledger.used_stakeholder_patterns, pattern)
    return ledger
