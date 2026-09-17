"""A6.1 — core upload runtime (lesson / avatar / teacher docs) unit tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from app.models.media import MediaAccessScope, MediaObject, MediaStatus, StorageProvider
from app.services.media_storage.constants import PRIVATE_BUCKET, PUBLIC_BUCKET
from app.services.media_storage.providers.supabase_provider import SupabaseStorageProvider
from app.services.media_storage.upload import (
    build_object_key,
    client_url_for_media,
    store_and_register_media,
)
from app.services.media_storage.validation import IMAGE_MIMES, validate_upload_bytes


class _FakeDb:
    def __init__(self) -> None:
        self._next_id = 1
        self.added: list = []

    def add(self, obj) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = self._next_id
                self._next_id += 1


def _patch_settings(monkeypatch, tmp_path: Path, **overrides):
    from app.core import config as config_mod
    from app.services import media_storage_service as mss
    from app.services.media_storage import config as storage_config
    from app.services.media_storage import upload as upload_mod

    base = {
        "MEDIA_STORAGE_PROVIDER": "local",
        "SUPABASE_URL": "",
        "SUPABASE_SERVICE_ROLE_KEY": "",
        "SUPABASE_PUBLIC_BUCKET": PUBLIC_BUCKET,
        "SUPABASE_PRIVATE_BUCKET": PRIVATE_BUCKET,
        "SUPABASE_SIGNED_URL_TTL_SECONDS": 120,
        "UPLOAD_DIR": str(tmp_path),
        "MAX_PDF_BYTES": 50 * 1024 * 1024,
        "MAX_AUDIO_BYTES": 25 * 1024 * 1024,
        "MAX_VIDEO_BYTES": 200 * 1024 * 1024,
    }
    base.update(overrides)
    settings = SimpleNamespace(**base)

    monkeypatch.setattr(config_mod, "get_settings", lambda: settings)
    monkeypatch.setattr(storage_config, "get_settings", lambda: settings)
    monkeypatch.setattr(upload_mod, "get_settings", lambda: settings)
    monkeypatch.setattr(mss, "get_settings", lambda: settings)
    monkeypatch.setattr(mss, "settings", settings)
    # Clear lru cache on the real get_settings if still wrapped.
    real_gs = getattr(config_mod.get_settings, "__wrapped__", None)
    if hasattr(config_mod.get_settings, "cache_clear"):
        config_mod.get_settings.cache_clear()
    return settings


def test_build_object_key_collision_safe_under_private_prefix():
    a = build_object_key("lessons", "teacher_1", "course_2", "lesson_3", "pdf", filename="x.pdf")
    b = build_object_key("lessons", "teacher_1", "course_2", "lesson_3", "pdf", filename="x.pdf")
    assert a.startswith("lessons/teacher_1/course_2/lesson_3/pdf/")
    assert a.endswith(".pdf")
    assert a != b


def test_client_url_never_leaks_absolute_path_for_supabase_private():
    media = MediaObject(
        id=42,
        storage_provider=StorageProvider.supabase.value,
        storage_bucket=PRIVATE_BUCKET,
        storage_key="lessons/teacher_1/course_2/lesson_3/pdf/abc.pdf",
        access_scope=MediaAccessScope.private.value,
        status=MediaStatus.ready.value,
        public_url=None,
    )
    url = client_url_for_media(media)
    assert url == "/api/media/42/download-url"
    assert ":\\" not in url
    assert "/Users/" not in url
    assert "C:" not in url


def test_client_url_uses_public_object_url_for_avatar():
    media = MediaObject(
        id=9,
        storage_provider=StorageProvider.supabase.value,
        storage_bucket=PUBLIC_BUCKET,
        storage_key="avatars/teacher_1/abc.png",
        access_scope=MediaAccessScope.public.value,
        status=MediaStatus.ready.value,
        public_url="https://example.supabase.co/storage/v1/object/public/edumind-public/avatars/teacher_1/abc.png",
    )
    assert client_url_for_media(media).startswith("https://example.supabase.co/")


@pytest.mark.asyncio
async def test_local_mode_lesson_upload_registers_media_and_writes_disk(monkeypatch, tmp_path):
    _patch_settings(monkeypatch, tmp_path, MEDIA_STORAGE_PROVIDER="local")
    db = _FakeDb()
    content = b"%PDF-1.4 local lesson"
    stored = await store_and_register_media(
        db,
        content=content,
        filename="lesson.pdf",
        mime_type="application/pdf",
        uploaded_by_user_id=7,
        access_scope=MediaAccessScope.private.value,
        object_key="lessons/teacher_7/course_1/lesson_1/pdf/file.pdf",
        kind="pdf",
        keep_local_working_copy=True,
    )
    assert stored.storage_provider == StorageProvider.local.value
    assert stored.storage_bucket is None
    assert stored.media.storage_key.endswith("file.pdf") or "lessons/" in stored.storage_key
    assert stored.client_url.startswith("/uploads/")
    assert stored.local_path is not None
    assert Path(stored.local_path).is_file()
    assert Path(stored.local_path).read_bytes() == content
    assert "C:\\Projects" not in stored.client_url


@pytest.mark.asyncio
async def test_supabase_mode_lesson_upload_private_bucket_and_mediaobject(monkeypatch, tmp_path):
    settings = _patch_settings(
        monkeypatch,
        tmp_path,
        MEDIA_STORAGE_PROVIDER="supabase",
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-service-role-placeholder",
    )
    uploaded: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        uploaded.append({"method": request.method, "url": str(request.url), "body": request.content})
        return httpx.Response(200, json={"Key": "ok"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        "app.services.media_storage.upload.SupabaseStorageProvider",
        lambda *a, **k: SupabaseStorageProvider(settings=settings, client=client),
    )

    db = _FakeDb()
    content = b"%PDF-1.4 supabase lesson"
    key = "lessons/teacher_7/course_1/lesson_9/pdf/abc123.pdf"
    stored = await store_and_register_media(
        db,
        content=content,
        filename="lesson.pdf",
        mime_type="application/pdf",
        uploaded_by_user_id=7,
        access_scope=MediaAccessScope.private.value,
        object_key=key,
        kind="pdf",
        keep_local_working_copy=True,
    )
    client.close()

    assert stored.storage_provider == StorageProvider.supabase.value
    assert stored.storage_bucket == PRIVATE_BUCKET
    assert stored.storage_key == key
    assert stored.access_scope == MediaAccessScope.private.value
    assert stored.media.mime_type == "application/pdf"
    assert stored.media.file_size_bytes == len(content)
    assert stored.media.status == MediaStatus.ready.value
    assert stored.client_url == f"/api/media/{stored.media.id}/download-url"
    assert stored.local_path is not None
    assert Path(stored.local_path).read_bytes() == content
    assert any(PRIVATE_BUCKET in u["url"] for u in uploaded)
    assert not any("service-role" in u["url"].lower() for u in uploaded)


@pytest.mark.asyncio
async def test_supabase_avatar_uses_public_bucket(monkeypatch, tmp_path):
    settings = _patch_settings(
        monkeypatch,
        tmp_path,
        MEDIA_STORAGE_PROVIDER="supabase",
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-service-role-placeholder",
    )
    uploaded_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        uploaded_urls.append(str(request.url))
        return httpx.Response(200, json={"Key": "ok"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        "app.services.media_storage.upload.SupabaseStorageProvider",
        lambda *a, **k: SupabaseStorageProvider(settings=settings, client=client),
    )
    db = _FakeDb()
    stored = await store_and_register_media(
        db,
        content=b"\x89PNG" + b"0" * 64,
        filename="avatar.png",
        mime_type="image/png",
        uploaded_by_user_id=3,
        access_scope=MediaAccessScope.public.value,
        object_key="avatars/teacher_3/avatar.png",
        kind="avatar",
    )
    client.close()
    assert stored.storage_bucket == PUBLIC_BUCKET
    assert stored.access_scope == MediaAccessScope.public.value
    assert "edumind-public" in stored.client_url
    assert any(PUBLIC_BUCKET in u for u in uploaded_urls)


@pytest.mark.asyncio
async def test_supabase_teacher_document_private(monkeypatch, tmp_path):
    settings = _patch_settings(
        monkeypatch,
        tmp_path,
        MEDIA_STORAGE_PROVIDER="supabase",
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-service-role-placeholder",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Key": "ok"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        "app.services.media_storage.upload.SupabaseStorageProvider",
        lambda *a, **k: SupabaseStorageProvider(settings=settings, client=client),
    )
    db = _FakeDb()
    key = "teacher-documents/teacher_5/cert.pdf"
    stored = await store_and_register_media(
        db,
        content=b"%PDF-1.4 cert",
        filename="cert.pdf",
        mime_type="application/pdf",
        uploaded_by_user_id=5,
        access_scope=MediaAccessScope.private.value,
        object_key=key,
        kind="teacher-document",
    )
    client.close()
    assert stored.storage_bucket == PRIVATE_BUCKET
    assert stored.storage_key.startswith("teacher-documents/")
    assert stored.client_url.startswith("/api/media/")


@pytest.mark.asyncio
async def test_misconfigured_supabase_falls_back_to_local_upload(monkeypatch, tmp_path):
    _patch_settings(
        monkeypatch,
        tmp_path,
        MEDIA_STORAGE_PROVIDER="supabase",
        SUPABASE_URL="",
        SUPABASE_SERVICE_ROLE_KEY="",
    )
    db = _FakeDb()
    stored = await store_and_register_media(
        db,
        content=b"%PDF-1.4 fallback",
        filename="a.pdf",
        mime_type="application/pdf",
        uploaded_by_user_id=1,
        access_scope=MediaAccessScope.private.value,
        object_key="lessons/teacher_1/course_1/lesson_1/pdf/a.pdf",
        kind="pdf",
    )
    assert stored.storage_provider == StorageProvider.local.value
    assert stored.client_url.startswith("/uploads/")


@pytest.mark.asyncio
async def test_upload_rejects_bad_mime_and_oversize(monkeypatch, tmp_path):
    _patch_settings(monkeypatch, tmp_path)
    db = _FakeDb()
    with pytest.raises(HTTPException) as bad_mime:
        await store_and_register_media(
            db,
            content=b"MZ exe",
            filename="x.exe",
            mime_type="application/x-msdownload",
            uploaded_by_user_id=1,
            access_scope=MediaAccessScope.public.value,
            object_key="avatars/teacher_1/x.exe",
            kind="avatar",
            max_bytes=1024,
        )
    assert bad_mime.value.status_code == 400

    with pytest.raises(HTTPException) as too_big:
        await store_and_register_media(
            db,
            content=b"0" * 200,
            filename="big.png",
            mime_type="image/png",
            uploaded_by_user_id=1,
            access_scope=MediaAccessScope.public.value,
            object_key="avatars/teacher_1/big.png",
            kind="avatar",
            max_bytes=50,
        )
    assert too_big.value.status_code == 400


def test_buckets_expected_by_code():
    assert PUBLIC_BUCKET == "edumind-public"
    assert PRIVATE_BUCKET == "edumind-private"


def test_validation_reuse():
    with pytest.raises(HTTPException):
        validate_upload_bytes(
            content=b"",
            filename="a.png",
            mime_type="image/png",
            allowed_mimes=IMAGE_MIMES,
            max_bytes=10,
        )
