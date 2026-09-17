"""Resolve authorized download URLs for MediaObject (A6.0)."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import MediaObject, StorageProvider
from app.models.user import User
from app.services.media_storage.access import assert_media_download_allowed
from app.services.media_storage.config import signed_url_ttl_seconds
from app.services.media_storage.providers.base import ResolvedDownload
from app.services.media_storage.providers.local import LocalStorageProvider
from app.services.media_storage.providers.supabase_provider import (
    SupabaseStorageError,
    SupabaseStorageProvider,
)


async def resolve_media_download_url(
    db: AsyncSession,
    *,
    media: MediaObject,
    user: User,
    expires_in: int | None = None,
) -> ResolvedDownload:
    """Authorize then resolve a download URL. Never exposes service-role credentials."""
    await assert_media_download_allowed(db, media=media, user=user)
    return resolve_media_download_url_authorized(media, expires_in=expires_in)


def resolve_media_download_url_authorized(
    media: MediaObject,
    *,
    expires_in: int | None = None,
) -> ResolvedDownload:
    """Resolve URL after authorization has already succeeded (or for tests)."""
    provider = (media.storage_provider or StorageProvider.local.value).strip().lower()
    ttl = expires_in if expires_in is not None else signed_url_ttl_seconds()

    if provider == StorageProvider.supabase.value:
        try:
            return SupabaseStorageProvider().resolve_media(media, expires_in=ttl)
        except SupabaseStorageError as exc:
            # Misconfigured supabase must not break local DEV — if object claims supabase
            # but provider is unavailable, fail closed for that object (not silent public leak).
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="تخزين الملفات السحابي غير متاح حالياً",
            ) from exc

    # local / unknown → local path resolution (existing /uploads behavior)
    return LocalStorageProvider().resolve_media(media)


def resolved_download_payload(resolved: ResolvedDownload) -> dict:
    data = asdict(resolved)
    # Never include credentials; payload is already URL-only.
    return data


async def get_media_or_404(db: AsyncSession, media_id: int) -> MediaObject:
    media = await db.get(MediaObject, media_id)
    if media is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الملف غير موجود")
    return media
