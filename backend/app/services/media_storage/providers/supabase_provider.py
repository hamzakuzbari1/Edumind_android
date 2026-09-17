"""Supabase Storage provider via REST (service role stays server-side only)."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from app.core.config import Settings, get_settings
from app.models.media import MediaObject, MediaAccessScope, StorageProvider
from app.services.media_storage.config import signed_url_ttl_seconds, supabase_configured
from app.services.media_storage.constants import (
    PRIVATE_BUCKET,
    PUBLIC_BUCKET,
    PROVIDER_SUPABASE,
    normalize_storage_key,
)
from app.services.media_storage.providers.base import ResolvedDownload


class SupabaseStorageError(RuntimeError):
    pass


class SupabaseStorageProvider:
    name = PROVIDER_SUPABASE

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None):
        self._settings = settings or get_settings()
        self._client = client

    @property
    def base_url(self) -> str:
        return (self._settings.SUPABASE_URL or "").rstrip("/")

    @property
    def service_role_key(self) -> str:
        return (self._settings.SUPABASE_SERVICE_ROLE_KEY or "").strip()

    @property
    def public_bucket(self) -> str:
        return (getattr(self._settings, "SUPABASE_PUBLIC_BUCKET", None) or PUBLIC_BUCKET).strip() or PUBLIC_BUCKET

    @property
    def private_bucket(self) -> str:
        return (getattr(self._settings, "SUPABASE_PRIVATE_BUCKET", None) or PRIVATE_BUCKET).strip() or PRIVATE_BUCKET

    def _headers(self) -> dict[str, str]:
        key = self.service_role_key
        return {
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Content-Type": "application/json",
        }

    def _upload_headers(self, content_type: str) -> dict[str, str]:
        key = self.service_role_key
        return {
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Content-Type": content_type or "application/octet-stream",
            "x-upsert": "true",
        }

    def _ensure_configured(self) -> None:
        if not supabase_configured(self._settings):
            raise SupabaseStorageError("supabase_not_configured")

    def upload_object(
        self,
        *,
        bucket: str,
        storage_key: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload bytes to Supabase Storage (service role; server-side only)."""
        self._ensure_configured()
        key = normalize_storage_key(storage_key)
        encoded = quote(key, safe="/")
        url = f"{self.base_url}/storage/v1/object/{bucket}/{encoded}"
        client = self._client or httpx.Client(timeout=120.0)
        owns_client = self._client is None
        try:
            response = client.post(
                url,
                headers=self._upload_headers(content_type),
                content=content,
            )
            # Some Supabase deployments use PUT for upsert.
            if response.status_code in {404, 405, 409}:
                response = client.put(
                    url,
                    headers=self._upload_headers(content_type),
                    content=content,
                )
        finally:
            if owns_client:
                client.close()
        if response.status_code >= 400:
            raise SupabaseStorageError(f"upload_failed:{response.status_code}")

    def public_object_url(self, *, bucket: str, storage_key: str) -> str:
        self._ensure_configured()
        key = normalize_storage_key(storage_key)
        encoded = quote(key, safe="/")
        return f"{self.base_url}/storage/v1/object/public/{bucket}/{encoded}"

    def create_signed_download_url(
        self,
        *,
        bucket: str,
        storage_key: str,
        expires_in: int,
    ) -> str:
        self._ensure_configured()
        key = normalize_storage_key(storage_key)
        encoded = quote(key, safe="/")
        url = f"{self.base_url}/storage/v1/object/sign/{bucket}/{encoded}"
        client = self._client or httpx.Client(timeout=20.0)
        owns_client = self._client is None
        try:
            response = client.post(
                url,
                headers=self._headers(),
                json={"expiresIn": int(expires_in)},
            )
        finally:
            if owns_client:
                client.close()
        if response.status_code >= 400:
            raise SupabaseStorageError(f"sign_failed:{response.status_code}")
        payload = response.json()
        signed = payload.get("signedURL") or payload.get("signedUrl") or payload.get("url")
        if not signed:
            raise SupabaseStorageError("sign_missing_url")
        signed = str(signed)
        if signed.startswith("http://") or signed.startswith("https://"):
            return signed
        if signed.startswith("/"):
            return f"{self.base_url}/storage/v1{signed}"
        return f"{self.base_url}/storage/v1/{signed.lstrip('/')}"

    def resolve_media(self, media: MediaObject, *, expires_in: int | None = None) -> ResolvedDownload:
        self._ensure_configured()
        bucket = (media.storage_bucket or "").strip()
        if not bucket:
            raise SupabaseStorageError("missing_bucket")
        key = normalize_storage_key(media.storage_key)
        if not key:
            raise SupabaseStorageError("missing_key")

        ttl = expires_in if expires_in is not None else signed_url_ttl_seconds(self._settings)
        scope = (media.access_scope or "").strip().lower()

        # Public scope may use permanent public object URL on the public bucket only.
        if scope == MediaAccessScope.public.value and bucket == self.public_bucket:
            return ResolvedDownload(
                url=self.public_object_url(bucket=bucket, storage_key=key),
                expires_in=None,
                provider=StorageProvider.supabase.value,
                is_signed=False,
                bucket=bucket,
            )

        # Private (and any non-public scope on supabase): always short-lived signed URL.
        # Never rely on permanent public_url for private objects.
        signed = self.create_signed_download_url(bucket=bucket, storage_key=key, expires_in=ttl)
        return ResolvedDownload(
            url=signed,
            expires_in=ttl,
            provider=StorageProvider.supabase.value,
            is_signed=True,
            bucket=bucket,
        )
