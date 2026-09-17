"""Storage helpers for speaking promotion readiness/stability (S17).

Namespaced under promotion_readiness_json['speaking_promotion'] — separate from
the knowledge-model speaking bucket.
"""

from __future__ import annotations

from typing import Any

SPEAKING_PROMOTION_KEY = "speaking_promotion"


def speaking_promotion_bucket_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    raw = payload.get(SPEAKING_PROMOTION_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def merge_speaking_promotion_into_payload(
    payload: dict[str, Any] | None,
    bucket: dict[str, Any],
) -> dict[str, Any]:
    out = dict(payload) if isinstance(payload, dict) else {}
    out[SPEAKING_PROMOTION_KEY] = dict(bucket)
    return out
