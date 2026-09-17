"""Persist Live Bridge bundle on progression JSONB payload (alongside discussion)."""

from __future__ import annotations

from typing import Any

from app.services.language_speaking_live_bridge.types import (
    SPEAKING_LIVE_BRIDGE_KEY,
    LiveBridgeBundle,
)
from app.services.language_speaking_knowledge_model.storage import SPEAKING_BUCKET_KEY


def live_bridge_from_payload(payload: dict[str, Any] | None) -> LiveBridgeBundle:
    if not isinstance(payload, dict):
        return LiveBridgeBundle()
    raw = payload.get(SPEAKING_LIVE_BRIDGE_KEY)
    if isinstance(raw, dict):
        return LiveBridgeBundle.from_dict(raw)
    # Legacy/nested under speaking bucket
    bucket = payload.get(SPEAKING_BUCKET_KEY)
    if isinstance(bucket, dict):
        nested = bucket.get(SPEAKING_LIVE_BRIDGE_KEY)
        if isinstance(nested, dict):
            return LiveBridgeBundle.from_dict(nested)
    return LiveBridgeBundle()


def merge_live_bridge_into_payload(
    payload: dict[str, Any] | None,
    bundle: LiveBridgeBundle,
) -> dict[str, Any]:
    out = dict(payload) if isinstance(payload, dict) else {}
    out[SPEAKING_LIVE_BRIDGE_KEY] = bundle.to_dict()
    return out


def live_bridge_from_speaking_bucket(speaking_bucket: dict[str, Any] | None) -> LiveBridgeBundle:
    if not isinstance(speaking_bucket, dict):
        return LiveBridgeBundle()
    raw = speaking_bucket.get(SPEAKING_LIVE_BRIDGE_KEY)
    return LiveBridgeBundle.from_dict(raw if isinstance(raw, dict) else None)


def merge_live_bridge_into_speaking_bucket(
    speaking_bucket: dict[str, Any] | None,
    bundle: LiveBridgeBundle,
) -> dict[str, Any]:
    bucket = dict(speaking_bucket) if isinstance(speaking_bucket, dict) else {}
    bucket[SPEAKING_LIVE_BRIDGE_KEY] = bundle.to_dict()
    return bucket
