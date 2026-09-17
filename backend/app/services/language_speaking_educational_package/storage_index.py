"""Resume / index helpers in promotion_readiness_json (capped; ELP-owned key)."""

from __future__ import annotations

from typing import Any

from app.services.language_educational_package.cache_policy import MAX_INDEXED_PACKAGES_PER_STUDENT

SPEAKING_ELP_INDEX_KEY = "speaking_educational_packages"


def empty_elp_index() -> dict[str, Any]:
    return {
        "by_fingerprint": {},
        "by_package_id": {},
        "active_by_mission": {},
        "order": [],
    }


def elp_index_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return empty_elp_index()
    raw = payload.get(SPEAKING_ELP_INDEX_KEY)
    if not isinstance(raw, dict):
        return empty_elp_index()
    return {
        "by_fingerprint": dict(raw.get("by_fingerprint") or {})
        if isinstance(raw.get("by_fingerprint"), dict)
        else {},
        "by_package_id": dict(raw.get("by_package_id") or {})
        if isinstance(raw.get("by_package_id"), dict)
        else {},
        "active_by_mission": dict(raw.get("active_by_mission") or {})
        if isinstance(raw.get("active_by_mission"), dict)
        else {},
        "order": list(raw.get("order") or []) if isinstance(raw.get("order"), list) else [],
    }


def merge_elp_index_into_payload(
    payload: dict[str, Any] | None,
    index: dict[str, Any],
) -> dict[str, Any]:
    out = dict(payload) if isinstance(payload, dict) else {}
    order = list(index.get("order") or [])[-MAX_INDEXED_PACKAGES_PER_STUDENT :]
    keep = set(order)
    by_fp = {
        k: v
        for k, v in dict(index.get("by_fingerprint") or {}).items()
        if v in keep or not keep
    }
    by_id = {
        k: v for k, v in dict(index.get("by_package_id") or {}).items() if k in keep or not keep
    }
    # Prefer keeping all mapped package ids that appear in order
    if keep:
        by_id = {k: v for k, v in dict(index.get("by_package_id") or {}).items() if k in keep}
        by_fp = {
            k: v for k, v in dict(index.get("by_fingerprint") or {}).items() if str(v) in keep
        }
    out[SPEAKING_ELP_INDEX_KEY] = {
        "by_fingerprint": by_fp,
        "by_package_id": by_id,
        "active_by_mission": dict(index.get("active_by_mission") or {}),
        "order": order,
    }
    return out


def record_package_in_index(
    payload: dict[str, Any] | None,
    *,
    package_id: str,
    constraints_fingerprint: str,
    mission_id: str,
    content_item_id: int,
) -> dict[str, Any]:
    index = elp_index_from_payload(payload)
    index["by_fingerprint"][constraints_fingerprint] = package_id
    index["by_package_id"][package_id] = content_item_id
    if mission_id:
        index["active_by_mission"][mission_id] = package_id
    order = [x for x in index["order"] if x != package_id]
    order.append(package_id)
    index["order"] = order[-MAX_INDEXED_PACKAGES_PER_STUDENT :]
    return merge_elp_index_into_payload(payload, index)
