"""Canonical Supabase Storage bucket + private object prefix constants (A6.0)."""

from __future__ import annotations

# Logical MVP buckets — only these two.
PUBLIC_BUCKET = "edumind-public"
PRIVATE_BUCKET = "edumind-private"

# Allowed private object prefixes (no ai-artifacts yet).
PRIVATE_PREFIXES: tuple[str, ...] = (
    "lessons/",
    "teacher-documents/",
    "teacher-voice/",
    "messages/",
    "student-audio/",
    "language/",
)

PROVIDER_LOCAL = "local"
PROVIDER_SUPABASE = "supabase"

DEFAULT_SIGNED_URL_TTL_SECONDS = 300
MIN_SIGNED_URL_TTL_SECONDS = 60
MAX_SIGNED_URL_TTL_SECONDS = 900


def normalize_storage_key(key: str) -> str:
    return (key or "").replace("\\", "/").lstrip("/")


def is_allowed_private_key(storage_key: str) -> bool:
    key = normalize_storage_key(storage_key)
    return any(key.startswith(prefix) for prefix in PRIVATE_PREFIXES)


def bucket_for_access_scope(access_scope: str) -> str:
    scope = (access_scope or "").strip().lower()
    if scope == "public":
        return PUBLIC_BUCKET
    return PRIVATE_BUCKET
