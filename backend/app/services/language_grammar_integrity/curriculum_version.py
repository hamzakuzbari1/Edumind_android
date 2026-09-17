"""Curriculum version pinning helpers (Wave D) — read-only; no YAML edits."""

from __future__ import annotations

# Product curriculum version from Wave A lock (index.yaml). Do not invent alternate versions.
CURRICULUM_VERSION_PIN = "1.1.0"


def get_curriculum_version() -> str:
    """Return pinned curriculum version for evidence / mastery metadata.

    Prefers the loaded catalog snapshot version when available; falls back to the
    Wave A lock pin. Never writes curriculum files.
    """
    try:
        from app.services.language_grammar_catalog.catalog import get_default_catalog

        snap = get_default_catalog()
        ver = str(getattr(snap, "version", "") or "").strip()
        if ver:
            return ver
    except Exception:  # noqa: BLE001 — integrity layer must not fail closed on catalog import
        pass
    return CURRICULUM_VERSION_PIN
