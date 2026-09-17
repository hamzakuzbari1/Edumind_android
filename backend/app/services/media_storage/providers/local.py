"""Local disk /uploads provider — existing DEV fallback (A6.0)."""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.models.media import MediaObject, StorageProvider
from app.services.media_storage.constants import PROVIDER_LOCAL, normalize_storage_key
from app.services.media_storage.providers.base import ResolvedDownload


class LocalStorageProvider:
    name = PROVIDER_LOCAL

    def public_object_url(self, *, bucket: str, storage_key: str) -> str:
        key = normalize_storage_key(storage_key)
        return "/uploads/" + key

    def create_signed_download_url(
        self,
        *,
        bucket: str,
        storage_key: str,
        expires_in: int,
    ) -> str:
        # Local mounts are not signed; return the same public path.
        return self.public_object_url(bucket=bucket, storage_key=storage_key)

    def resolve_media(self, media: MediaObject) -> ResolvedDownload:
        if media.public_url and media.public_url.strip():
            url = media.public_url.strip()
        else:
            url = self.public_object_url(bucket="", storage_key=media.storage_key)
        return ResolvedDownload(
            url=url,
            expires_in=None,
            provider=StorageProvider.local.value,
            is_signed=False,
            bucket=None,
        )

    def local_disk_path(self, media: MediaObject) -> Path | None:
        key = normalize_storage_key(media.storage_key)
        if not key:
            return None
        root = Path(get_settings().UPLOAD_DIR).resolve()
        path = (root / key).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            return None
        return path if path.is_file() else None
