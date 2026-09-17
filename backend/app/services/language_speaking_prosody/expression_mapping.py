"""Map Hume expression labels to stable canonical tags (S6)."""

from __future__ import annotations

import re


def normalize_expression_label(label: str) -> str:
    """Convert provider label to stable expression:<snake> tag."""
    raw = (label or "").strip()
    if not raw:
        return "expression:unknown"
    snake = re.sub(r"[^a-zA-Z0-9]+", "_", raw).strip("_").lower()
    return f"expression:{snake}" if snake else "expression:unknown"
