"""A6.0 — Supabase storage foundation unit tests (no real secrets / no network)."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from app.models.media import MediaAccessScope, MediaObject, MediaStatus, StorageProvider
from app.models.user import User, UserRole
from app.services.media_storage.access import assert_media_download_allowed
from app.services.media_storage.config import (
    effective_storage_provider,
    supabase_configured,
    supabase_storage_enabled,
)
from app.services.media_storage.constants import (
    PRIVATE_BUCKET,
    PRIVATE_PREFIXES,
    PUBLIC_BUCKET,
    is_allowed_private_key,
)
from app.services.media_storage.download import resolve_media_download_url_authorized
from app.services.media_storage.providers.local import LocalStorageProvider
from app.services.media_storage.providers.supabase_provider import (
    SupabaseStorageError,
    SupabaseStorageProvider,
)
from app.services.media_storage.validation import (
    IMAGE_MIMES,
    validate_upload_bytes,
)


def _settings(**overrides):
    base = {
        "MEDIA_STORAGE_PROVIDER": "local",
        "SUPABASE_URL": "",
        "SUPABASE_SERVICE_ROLE_KEY": "",
        "SUPABASE_PUBLIC_BUCKET": PUBLIC_BUCKET,
        "SUPABASE_PRIVATE_BUCKET": PRIVATE_BUCKET,
        "SUPABASE_SIGNED_URL_TTL_SECONDS": 120,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_private_prefixes_include_mvp_paths_only():
    assert "lessons/" in PRIVATE_PREFIXES
    assert "teacher-documents/" in PRIVATE_PREFIXES
    assert "teacher-voice/" in PRIVATE_PREFIXES
    assert "messages/" in PRIVATE_PREFIXES
    assert "student-audio/" in PRIVATE_PREFIXES
    assert "language/" in PRIVATE_PREFIXES
    assert not any(p.startswith("ai-") for p in PRIVATE_PREFIXES)
    assert is_allowed_private_key("lessons/course_1/file.pdf")
    assert not is_allowed_private_key("ai-artifacts/x.bin")


def test_missing_supabase_config_falls_back_to_local():
    s = _settings(MEDIA_STORAGE_PROVIDER="supabase", SUPABASE_URL="", SUPABASE_SERVICE_ROLE_KEY="")
    assert supabase_configured(s) is False
    assert supabase_storage_enabled(s) is False
    assert effective_storage_provider(s) == "local"


def test_supabase_enabled_only_with_credentials():
    s = _settings(
        MEDIA_STORAGE_PROVIDER="supabase",
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-service-role-placeholder",
    )
    assert supabase_configured(s) is True
    assert supabase_storage_enabled(s) is True
    assert effective_storage_provider(s) == "supabase"


def test_local_provider_resolves_existing_public_url():
    media = MediaObject(
        storage_provider=StorageProvider.local.value,
        storage_key="teacher_1/lessons/a.pdf",
        public_url="/uploads/teacher_1/lessons/a.pdf",
        access_scope=MediaAccessScope.legacy_public.value,
        status=MediaStatus.ready.value,
    )
    resolved = LocalStorageProvider().resolve_media(media)
    assert resolved.provider == "local"
    assert resolved.url == "/uploads/teacher_1/lessons/a.pdf"
    assert resolved.is_signed is False
    assert resolved.expires_in is None


def test_local_provider_builds_uploads_path_when_public_url_missing():
    media = MediaObject(
        storage_provider=StorageProvider.local.value,
        storage_key="messages/thread_9/voice.webm",
        public_url=None,
        access_scope=MediaAccessScope.private.value,
        status=MediaStatus.ready.value,
    )
    resolved = resolve_media_download_url_authorized(media)
    assert resolved.url == "/uploads/messages/thread_9/voice.webm"
    assert resolved.provider == "local"


def test_supabase_private_uses_signed_url_not_permanent_public(monkeypatch):
    settings = _settings(
        MEDIA_STORAGE_PROVIDER="supabase",
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-service-role-placeholder",
        SUPABASE_SIGNED_URL_TTL_SECONDS=180,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert "service-role" not in request.url.path
        assert request.headers.get("apikey") == "test-service-role-placeholder"
        assert request.headers.get("Authorization") == "Bearer test-service-role-placeholder"
        return httpx.Response(200, json={"signedURL": "/object/sign/edumind-private/lessons/a.pdf?token=abc"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = SupabaseStorageProvider(settings=settings, client=client)

    media = MediaObject(
        storage_provider=StorageProvider.supabase.value,
        storage_bucket=PRIVATE_BUCKET,
        storage_key="lessons/a.pdf",
        public_url="https://example.supabase.co/storage/v1/object/public/edumind-private/lessons/a.pdf",
        access_scope=MediaAccessScope.private.value,
        status=MediaStatus.ready.value,
    )
    resolved = provider.resolve_media(media)
    assert resolved.is_signed is True
    assert resolved.expires_in == 180
    assert "token=abc" in resolved.url
    assert "/object/sign/" in resolved.url
    # Must not return the permanent private "public" URL
    assert "object/public/edumind-private" not in resolved.url
    client.close()


def test_supabase_public_scope_uses_public_url():
    settings = _settings(
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-service-role-placeholder",
    )
    provider = SupabaseStorageProvider(settings=settings, client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))))
    media = MediaObject(
        storage_provider=StorageProvider.supabase.value,
        storage_bucket=PUBLIC_BUCKET,
        storage_key="avatars/u1.png",
        access_scope=MediaAccessScope.public.value,
        status=MediaStatus.ready.value,
    )
    resolved = provider.resolve_media(media)
    assert resolved.is_signed is False
    assert resolved.expires_in is None
    assert resolved.url.endswith("/object/public/edumind-public/avatars/u1.png")
    provider._client.close()


def test_supabase_sign_failure_raises():
    settings = _settings(
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-service-role-placeholder",
    )
    transport = httpx.MockTransport(lambda r: httpx.Response(401, json={"message": "no"}))
    client = httpx.Client(transport=transport)
    provider = SupabaseStorageProvider(settings=settings, client=client)
    with pytest.raises(SupabaseStorageError):
        provider.create_signed_download_url(
            bucket=PRIVATE_BUCKET,
            storage_key="lessons/x.pdf",
            expires_in=60,
        )
    client.close()


@pytest.mark.asyncio
async def test_private_media_unauthorized_rejected():
    media = MediaObject(
        id=7,
        storage_provider=StorageProvider.supabase.value,
        storage_bucket=PRIVATE_BUCKET,
        storage_key="lessons/secret.pdf",
        access_scope=MediaAccessScope.private.value,
        status=MediaStatus.ready.value,
        uploaded_by_user_id=99,
        metadata_json={},
    )
    user = User(id=1, email="s@example.com", name="S", hashed_password="x", role=UserRole.student)

    class _FakeResult:
        def scalar_one_or_none(self):
            return None

        def scalar(self):
            return None

    class _FakeDb:
        async def get(self, model, pk):
            return None

        async def scalar(self, *args, **kwargs):
            return None

        def execute(self, *args, **kwargs):
            raise AssertionError("should use scalar helpers")

    with pytest.raises(HTTPException) as exc:
        await assert_media_download_allowed(_FakeDb(), media=media, user=user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_uploader_authorized_for_private_media():
    media = MediaObject(
        id=7,
        storage_provider=StorageProvider.local.value,
        storage_key="student-audio/7/a.webm",
        access_scope=MediaAccessScope.private.value,
        status=MediaStatus.ready.value,
        uploaded_by_user_id=42,
    )
    user = User(id=42, email="s@example.com", name="S", hashed_password="x", role=UserRole.student)

    class _FakeDb:
        async def get(self, *a, **k):
            return None

        async def scalar(self, *a, **k):
            return None

    await assert_media_download_allowed(_FakeDb(), media=media, user=user)


@pytest.mark.asyncio
async def test_public_scope_allows_authenticated_user():
    media = MediaObject(
        id=3,
        storage_provider=StorageProvider.supabase.value,
        storage_bucket=PUBLIC_BUCKET,
        storage_key="banners/c1.png",
        access_scope=MediaAccessScope.public.value,
        status=MediaStatus.ready.value,
    )
    user = User(id=1, email="s@example.com", name="S", hashed_password="x", role=UserRole.student)

    class _FakeDb:
        async def scalar(self, *a, **k):
            return None

    await assert_media_download_allowed(_FakeDb(), media=media, user=user)


def test_mime_size_validation_primitives():
    ok = validate_upload_bytes(
        content=b"abc",
        filename="a.png",
        mime_type="image/png",
        allowed_mimes=IMAGE_MIMES,
        max_bytes=10,
    )
    assert ok.size_bytes == 3
    assert ok.mime_type == "image/png"

    with pytest.raises(HTTPException) as empty:
        validate_upload_bytes(
            content=b"",
            filename="a.png",
            mime_type="image/png",
            allowed_mimes=IMAGE_MIMES,
            max_bytes=10,
        )
    assert empty.value.status_code == 400

    with pytest.raises(HTTPException) as too_big:
        validate_upload_bytes(
            content=b"0123456789abc",
            filename="a.png",
            mime_type="image/png",
            allowed_mimes=IMAGE_MIMES,
            max_bytes=10,
        )
    assert too_big.value.status_code == 400

    with pytest.raises(HTTPException) as bad_mime:
        validate_upload_bytes(
            content=b"abc",
            filename="a.exe",
            mime_type="application/x-msdownload",
            allowed_mimes=IMAGE_MIMES,
            max_bytes=10,
        )
    assert bad_mime.value.status_code == 400


def test_resolve_authorized_supabase_object_fails_closed_without_config(monkeypatch):
    media = MediaObject(
        storage_provider=StorageProvider.supabase.value,
        storage_bucket=PRIVATE_BUCKET,
        storage_key="lessons/a.pdf",
        access_scope=MediaAccessScope.private.value,
        status=MediaStatus.ready.value,
    )
    # Clear process settings so provider sees empty credentials
    from app.core import config as config_mod

    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    config_mod.get_settings.cache_clear()
    with pytest.raises(HTTPException) as exc:
        resolve_media_download_url_authorized(media)
    assert exc.value.status_code == 503
    config_mod.get_settings.cache_clear()


def test_service_role_never_in_resolved_payload():
    media = MediaObject(
        storage_provider=StorageProvider.local.value,
        storage_key="x.pdf",
        public_url="/uploads/x.pdf",
        access_scope=MediaAccessScope.legacy_public.value,
        status=MediaStatus.ready.value,
    )
    resolved = resolve_media_download_url_authorized(media)
    blob = str(resolved)
    assert "SERVICE_ROLE" not in blob
    assert "service_role" not in blob.lower()
