"""Public URLs for uploaded files (avatars, lesson media)."""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


def public_upload_url(path: str | None) -> str | None:
    if not path:
        return None
    raw = path.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if raw.startswith("/uploads/") or raw.startswith("/api/media/"):
        return raw
    if raw.startswith("uploads/"):
        return "/" + raw.lstrip("/")
    try:
        rel = Path(raw).resolve().relative_to(Path(settings.UPLOAD_DIR).resolve())
        return "/uploads/" + "/".join(rel.parts)
    except Exception:
        if raw.startswith("/"):
            return raw
        return None


def teacher_avatar_url(path: str | None) -> str | None:
    """Public avatar path; unique upload filenames avoid stale browser cache."""
    return public_upload_url(path)
