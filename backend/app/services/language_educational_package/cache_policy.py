"""Cache / invalidation policy for frozen packages."""

from __future__ import annotations

MAX_INDEXED_PACKAGES_PER_STUDENT = 40
CACHE_KEY_FIELDS = ("skill", "constraints_fingerprint", "author_version", "locale")


def should_regenerate(
    *,
    stored_blueprint_hash: str,
    current_blueprint_hash: str,
    stored_author_version: str,
    current_author_version: str,
    stored_schema_version: str = "",
    current_schema_version: str = "",
) -> bool:
    if stored_blueprint_hash != current_blueprint_hash:
        return True
    if stored_author_version != current_author_version:
        return True
    if current_schema_version and stored_schema_version != current_schema_version:
        return True
    return False
