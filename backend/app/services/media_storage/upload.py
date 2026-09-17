"""A6.1 — store bytes via configured provider (local or Supabase) + MediaObject."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.media import MediaAccessScope, MediaObject, MediaStatus, StorageProvider
from app.services.media_storage.config import effective_storage_provider
from app.services.media_storage.constants import (
    PRIVATE_BUCKET,
    PUBLIC_BUCKET,
    normalize_storage_key,
)
from app.services.media_storage.providers.supabase_provider import (
    SupabaseStorageError,
    SupabaseStorageProvider,
)
from app.services.media_storage.validation import (
    AUDIO_MIMES,
    DOCUMENT_MIMES,
    IMAGE_MIMES,
    PDF_MIMES,
    VIDEO_MIMES,
    default_max_bytes_for_mime,
    extension_of,
    normalize_mime,
    validate_upload_bytes,
)
from app.services.media_storage.metadata import register_media_object

_SAFE_SEGMENT = re.compile(r"[^a-zA-Z0-9._-]+")


@dataclass(frozen=True)
class StoredUpload:
    media: MediaObject
    storage_provider: str
    storage_bucket: str | None
    storage_key: str
    access_scope: str
    # Local working path when a disk copy exists (lesson processing); never expose raw
    # absolute paths for supabase objects in API responses — use client_url instead.
    local_path: str | None
    client_url: str
    mime_type: str
    size_bytes: int


def _safe_segment(value: str) -> str:
    cleaned = _SAFE_SEGMENT.sub("_", (value or "").strip())
    return cleaned.strip("._") or "x"


def build_object_key(*segments: str, filename: str) -> str:
    """Deterministic collision-safe object key (uuid filename leaf)."""
    ext = extension_of(filename) or ""
    leaf = f"{uuid.uuid4().hex}{ext}"
    parts = [_safe_segment(s) for s in segments if s]
    parts.append(leaf)
    return normalize_storage_key("/".join(parts))


def _infer_mime(filename: str, mime_type: str | None) -> str:
    mime = normalize_mime(mime_type)
    if mime and mime != "application/octet-stream":
        return mime
    ext = extension_of(filename)
    return {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
    }.get(ext, mime or "application/octet-stream")


def _allowed_mimes_for_kind(kind: str) -> frozenset[str]:
    kind = (kind or "").lower()
    if kind in {"avatar", "image"}:
        return IMAGE_MIMES
    if kind in {"pdf", "homework"}:
        return PDF_MIMES | frozenset({"application/octet-stream"})
    if kind in {"document", "teacher-document"}:
        return DOCUMENT_MIMES | IMAGE_MIMES | frozenset({"application/octet-stream"})
    if kind in {"video"}:
        return VIDEO_MIMES | frozenset({"application/octet-stream"})
    if kind in {"audio", "lesson-audio"}:
        return AUDIO_MIMES | frozenset({"application/octet-stream"})
    return IMAGE_MIMES | PDF_MIMES | VIDEO_MIMES | AUDIO_MIMES | DOCUMENT_MIMES


def client_url_for_media(media: MediaObject) -> str:
    """API-safe URL — never returns filesystem absolute paths or service credentials."""
    provider = (media.storage_provider or "").strip().lower()
    if provider == StorageProvider.supabase.value:
        scope = (media.access_scope or "").strip().lower()
        # Public-safe objects: permanent public object URL (stored on media.public_url).
        if scope == MediaAccessScope.public.value and media.public_url:
            return media.public_url.strip()
        if scope == MediaAccessScope.public.value and media.storage_bucket and media.storage_key:
            try:
                return SupabaseStorageProvider().public_object_url(
                    bucket=media.storage_bucket,
                    storage_key=media.storage_key,
                )
            except SupabaseStorageError:
                pass
        # Private supabase objects: resolve via signed download endpoint (no path leak).
        return f"/api/media/{media.id}/download-url"
    if media.public_url and media.public_url.strip():
        url = media.public_url.strip()
        if url.startswith("http://") or url.startswith("https://") or url.startswith("/uploads/"):
            return url
    key = normalize_storage_key(media.storage_key)
    return f"/uploads/{key}" if key else f"/api/media/{media.id}/download-url"


def _write_local_copy(*, relative_key: str, content: bytes) -> tuple[str, str]:
    """Write under UPLOAD_DIR; return (absolute_path, /uploads public url)."""
    settings = get_settings()
    root = Path(settings.UPLOAD_DIR).resolve()
    dest = root / relative_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    public = "/uploads/" + "/".join(Path(relative_key).parts)
    return str(dest), public


async def store_and_register_media(
    db: AsyncSession,
    *,
    content: bytes,
    filename: str,
    mime_type: str | None,
    uploaded_by_user_id: int,
    access_scope: str,
    object_key: str,
    kind: str,
    max_bytes: int | None = None,
    metadata_json: dict | None = None,
    keep_local_working_copy: bool = False,
) -> StoredUpload:
    """
    Upload bytes to the effective provider and create a MediaObject.

    When supabase is active:
    - bytes are uploaded to the correct bucket/key
    - MediaObject records supabase provider/bucket/key
    - optional local working copy for lesson processing (not leaked in client_url)
    When local (default / fallback):
    - bytes land under UPLOAD_DIR as today
    """
    mime = _infer_mime(filename, mime_type)
    allowed = _allowed_mimes_for_kind(kind)
    limit = max_bytes if max_bytes is not None else default_max_bytes_for_mime(mime)
    validate_upload_bytes(
        content=content,
        filename=filename,
        mime_type=mime,
        allowed_mimes=allowed,
        max_bytes=limit,
    )

    scope = (access_scope or MediaAccessScope.private.value).strip().lower()
    key = normalize_storage_key(object_key)
    if not key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="مسار التخزين غير صالح")

    provider = effective_storage_provider()
    checksum = hashlib.sha256(content).hexdigest()
    local_path: str | None = None
    bucket: str | None = None

    if provider == StorageProvider.supabase.value:
        bucket = PUBLIC_BUCKET if scope == MediaAccessScope.public.value else PRIVATE_BUCKET
        try:
            SupabaseStorageProvider().upload_object(
                bucket=bucket,
                storage_key=key,
                content=content,
                content_type=mime,
            )
        except SupabaseStorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="تعذر رفع الملف إلى التخزين السحابي",
            ) from exc

        if keep_local_working_copy:
            # Relative key mirrors object key so processors can open a local path.
            local_path, _ = _write_local_copy(relative_key=key, content=content)

        media = await register_media_object(
            db,
            storage_path=key,
            storage_provider=StorageProvider.supabase.value,
            storage_key=key,
            storage_bucket=bucket,
            access_scope=scope,
            status=MediaStatus.ready.value,
            mime_type=mime,
            file_size_bytes=len(content),
            original_filename=filename,
            uploaded_by_user_id=uploaded_by_user_id,
            metadata_json=metadata_json,
            checksum_sha256=checksum,
        )
        # Persist public URL for public-scope assets (avatar).
        if scope == MediaAccessScope.public.value and bucket == PUBLIC_BUCKET:
            media.public_url = SupabaseStorageProvider().public_object_url(
                bucket=bucket,
                storage_key=key,
            )
            await db.flush()
    else:
        local_path, public = _write_local_copy(relative_key=key, content=content)
        media = await register_media_object(
            db,
            storage_path=public,
            storage_provider=StorageProvider.local.value,
            storage_key=key,
            storage_bucket=None,
            access_scope=scope if scope != MediaAccessScope.private.value else MediaAccessScope.legacy_public.value,
            status=MediaStatus.ready.value,
            mime_type=mime,
            file_size_bytes=len(content),
            original_filename=filename,
            uploaded_by_user_id=uploaded_by_user_id,
            metadata_json=metadata_json,
            checksum_sha256=checksum,
        )
        # Force public_url to /uploads form (register already does this for local).
        media.public_url = public
        await db.flush()

    return StoredUpload(
        media=media,
        storage_provider=media.storage_provider,
        storage_bucket=media.storage_bucket,
        storage_key=media.storage_key,
        access_scope=media.access_scope,
        local_path=local_path,
        client_url=client_url_for_media(media),
        mime_type=mime,
        size_bytes=len(content),
    )
