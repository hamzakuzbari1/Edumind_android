"""Deterministic content hashing for canonical grammar lesson revisions."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def compute_canonical_lesson_content_hash(
    *,
    student_content_json: dict[str, Any],
    server_teaching_metadata_json: dict[str, Any],
    schema_version: str,
    methodology_version: str,
) -> str:
    """Hash only stable educational payload, never timestamps or diagnostics."""

    payload = {
        "methodology_version": methodology_version,
        "schema_version": schema_version,
        "server_teaching_metadata_json": server_teaching_metadata_json,
        "student_content_json": student_content_json,
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
