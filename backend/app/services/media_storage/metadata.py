"""Media metadata persistence shared by storage services."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import MediaAccessScope, MediaObject, MediaStatus, StorageProvider
from app.services.media_storage.constants import (
    PRIVATE_BUCKET,
    bucket_for_access_scope,
    normalize_storage_key,
)
from app.services.media_storage.config import effective_storage_provider


def _public_url_for_path(storage_path: str) -> str:
    path = storage_path.replace("\\", "/")
    if path.startswith("/uploads/"):
        return path
    if path.startswith("uploads/"):
        return "/" + path
    return "/uploads/" + path.lstrip("/")


async def register_media_object(
    db: AsyncSession,
    *,
    storage_path: str,
    mime_type: str | None = None,
    file_size_bytes: int | None = None,
    original_filename: str | None = None,
    uploaded_by_user_id: int | None = None,
    storage_provider: str = StorageProvider.local.value,
    storage_key: str | None = None,
    storage_bucket: str | None = None,
    access_scope: str | None = None,
    status: str = MediaStatus.ready.value,
    metadata_json: dict | None = None,
    checksum_sha256: str | None = None,
) -> MediaObject:
    """Persist media metadata; binary is already stored by the caller."""
    provider = (storage_provider or StorageProvider.local.value).strip().lower()
    if provider == StorageProvider.supabase.value and effective_storage_provider() != StorageProvider.supabase.value:
        provider = StorageProvider.local.value

    key = normalize_storage_key(storage_key or storage_path)
    scope = (access_scope or MediaAccessScope.legacy_public.value).strip().lower()
    bucket = storage_bucket
    public_url: str | None

    if provider == StorageProvider.supabase.value:
        bucket = (bucket or bucket_for_access_scope(scope)).strip()
        # Private objects are resolved through a short-lived signed URL.
        public_url = None
        if not bucket:
            bucket = PRIVATE_BUCKET
    else:
        public_url = _public_url_for_path(storage_path)
        bucket = None

    media = MediaObject(
        storage_provider=provider,
        storage_key=key,
        storage_bucket=bucket,
        public_url=public_url,
        access_scope=scope,
        status=status,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        original_filename=original_filename,
        uploaded_by_user_id=uploaded_by_user_id,
        metadata_json=metadata_json,
        checksum_sha256=checksum_sha256,
    )
    db.add(media)
    await db.flush()
    return media
