"""Fingerprints for constraints and package content."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.services.language_educational_package.constraints import PackageConstraints
from app.services.language_educational_package.types import ELP_AUTHOR_VERSION, EducationalPackage


def _stable_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_constraints_fingerprint(constraints: PackageConstraints) -> str:
    payload = constraints.to_dict()
    digest = hashlib.sha256(_stable_dumps(payload).encode("utf-8")).hexdigest()
    return f"elp_c_{digest[:32]}"


def compute_content_fingerprint(package: EducationalPackage) -> str:
    """Hash educational content only (exclude package_id / status / fingerprints)."""
    payload = package.to_dict()
    for key in (
        "package_id",
        "status",
        "constraints_fingerprint",
        "content_fingerprint",
        "progression_metadata",
    ):
        payload.pop(key, None)
    payload["author_version"] = package.author_version or ELP_AUTHOR_VERSION
    digest = hashlib.sha256(_stable_dumps(payload).encode("utf-8")).hexdigest()
    return f"elp_p_{digest[:32]}"
