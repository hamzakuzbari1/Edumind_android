"""Provider-agnostic media storage — local disk today, Supabase when configured (A6.0)."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import get_settings
from app.services.media_storage.metadata import register_media_object

settings = get_settings()


def save_local_file(
    *,
    user_id: int,
    category: str,
    content: bytes,
    filename: str,
) -> tuple[str, str]:
    """Write bytes under UPLOAD_DIR and return (absolute_path, public_url)."""
    ext = Path(filename).suffix or ""
    root = Path(settings.UPLOAD_DIR) / f"teacher_{user_id}" / category
    root.mkdir(parents=True, exist_ok=True)
    dest = root / f"{uuid.uuid4().hex}{ext}"
    dest.write_bytes(content)
    rel = dest.resolve().relative_to(Path(settings.UPLOAD_DIR).resolve())
    public = "/uploads/" + "/".join(rel.parts)
    return str(dest), public


__all__ = ["get_settings", "register_media_object", "save_local_file", "settings"]
