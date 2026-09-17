"""Authorized MediaObject download URL resolution (A6.0 foundation)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.media_storage.download import (
    get_media_or_404,
    resolve_media_download_url,
)

router = APIRouter(prefix="/media", tags=["media"])


class MediaDownloadUrlOut(BaseModel):
    media_id: int
    url: str
    expires_in: int | None = None
    provider: str
    is_signed: bool
    bucket: str | None = None


@router.get("/{media_id}/download-url", response_model=MediaDownloadUrlOut)
async def media_download_url(
    media_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    expires_in: int | None = None,
):
    """
    Resolve a short-lived download URL for a MediaObject.

    Private objects require authorization (enrollment / ownership / thread membership).
    Public-scope objects on the public bucket may return a permanent public URL.
    Service-role credentials are never returned.
    """
    media = await get_media_or_404(db, media_id)
    resolved = await resolve_media_download_url(
        db,
        media=media,
        user=user,
        expires_in=expires_in,
    )
    return MediaDownloadUrlOut(
        media_id=media.id,
        url=resolved.url,
        expires_in=resolved.expires_in,
        provider=resolved.provider,
        is_signed=resolved.is_signed,
        bucket=resolved.bucket,
    )
