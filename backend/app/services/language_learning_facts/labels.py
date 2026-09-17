"""Shared slug → display label helper (non-narrative)."""

from __future__ import annotations


def slug_label(slug: str) -> str:
    return str(slug or "").replace("_", " ").strip()
