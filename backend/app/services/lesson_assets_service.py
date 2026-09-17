"""Multi-asset lessons: video + PDF + homework on one lesson row."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.lesson import Lesson, LessonAsset, LessonAssetType
from app.models.media import MediaAccessScope, MediaObject
from app.services.media_storage.upload import (
    build_object_key,
    client_url_for_media,
    store_and_register_media,
)
from app.utils.media_urls import public_upload_url

settings = get_settings()


def public_url(path: str | None) -> str | None:
    return public_upload_url(path)


def asset_map_from_lesson(lesson: Lesson) -> dict[str, LessonAsset]:
    """Build type → asset from relationship or legacy columns."""
    out: dict[str, LessonAsset] = {}
    if "assets" in inspect(lesson).unloaded:
        return out
    for asset in lesson.assets or []:
        t = asset.asset_type.value if hasattr(asset.asset_type, "value") else str(asset.asset_type)
        out[t] = asset
    return out


def paths_from_lesson(lesson: Lesson) -> dict[str, str | None]:
    """Resolved storage paths: video, pdf, homework, audio."""
    amap = asset_map_from_lesson(lesson)
    video = amap.get(LessonAssetType.video.value)
    pdf = amap.get(LessonAssetType.pdf.value)
    hw = amap.get(LessonAssetType.homework.value)
    audio = amap.get(LessonAssetType.audio.value)
    return {
        "video": video.storage_path if video else lesson.video_url,
        "pdf": pdf.storage_path if pdf else lesson.pdf_path,
        "homework": hw.storage_path if hw else lesson.homework_path,
        "audio": audio.storage_path if audio else lesson.voice_path,
    }


def sync_lesson_legacy_columns(lesson: Lesson) -> None:
    """Keep legacy columns in sync for existing AI/upload code."""
    paths = paths_from_lesson(lesson)
    lesson.video_url = paths["video"]
    lesson.pdf_path = paths["pdf"]
    lesson.homework_path = paths["homework"]


async def load_lesson_with_assets(db: AsyncSession, lesson_id: int) -> Lesson | None:
    result = await db.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.assets).selectinload(LessonAsset.media_object))
    )
    lesson = result.scalar_one_or_none()
    if lesson:
        sync_lesson_legacy_columns(lesson)
    return lesson


def _sync_legacy_column_for_asset(lesson: Lesson, asset_type: LessonAssetType, storage_path: str) -> None:
    """Update legacy path columns without lazy-loading lesson.assets (async-safe)."""
    if asset_type == LessonAssetType.video:
        lesson.video_url = storage_path
    elif asset_type == LessonAssetType.pdf:
        lesson.pdf_path = storage_path
    elif asset_type == LessonAssetType.homework:
        lesson.homework_path = storage_path
    elif asset_type == LessonAssetType.audio:
        lesson.voice_path = storage_path


def _asset_client_url(asset: LessonAsset) -> str | None:
    """Client-facing URL; prefers MediaObject resolution (no absolute path leaks)."""
    try:
        unloaded = inspect(asset).unloaded
    except Exception:
        unloaded = set()
    if "media_object" not in unloaded and asset.media_object is not None:
        return client_url_for_media(asset.media_object)
    return public_url(asset.storage_path)


async def upsert_asset(
    db: AsyncSession,
    lesson: Lesson,
    asset_type: LessonAssetType,
    storage_path: str,
    *,
    media: MediaObject | None = None,
    original_filename: str | None = None,
    mime_type: str | None = None,
    file_size_bytes: int | None = None,
    uploaded_by_user_id: int | None = None,
) -> LessonAsset:
    result = await db.execute(
        select(LessonAsset)
        .where(
            LessonAsset.lesson_id == lesson.id,
            LessonAsset.asset_type == asset_type,
        )
        .order_by(LessonAsset.sort_order.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()

    if media is None:
        from app.services.media_storage_service import register_media_object

        media = await register_media_object(
            db,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            original_filename=original_filename,
            uploaded_by_user_id=uploaded_by_user_id,
        )

    if existing:
        existing.storage_path = storage_path
        existing.media_object_id = media.id
        existing.media_object = media
        existing.mime_type = mime_type
        existing.file_size_bytes = file_size_bytes
        if original_filename:
            existing.original_filename = original_filename
        asset = existing
    else:
        sort_hint = {"video": 0, "pdf": 1, "homework": 2, "audio": 3}.get(asset_type.value, 10)
        asset = LessonAsset(
            lesson_id=lesson.id,
            asset_type=asset_type,
            storage_path=storage_path,
            media_object_id=media.id,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            original_filename=original_filename,
            sort_order=sort_hint,
        )
        asset.media_object = media
        db.add(asset)

    _sync_legacy_column_for_asset(lesson, asset_type, storage_path)
    await db.flush()
    return asset


async def save_lesson_file(
    db: AsyncSession,
    lesson: Lesson,
    asset_type: LessonAssetType,
    content: bytes,
    filename: str,
    *,
    user_id: int,
    course_id: int,
    mime_type: str | None = None,
) -> LessonAsset:
    """Store lesson asset via configured provider; keep local working copy for AI/OCR."""
    kind = asset_type.value
    object_key = build_object_key(
        "lessons",
        f"teacher_{user_id}",
        f"course_{course_id}",
        f"lesson_{lesson.id}",
        kind,
        filename=filename or f"{kind}.bin",
    )
    stored = await store_and_register_media(
        db,
        content=content,
        filename=filename or f"{kind}.bin",
        mime_type=mime_type,
        uploaded_by_user_id=user_id,
        access_scope=MediaAccessScope.private.value,
        object_key=object_key,
        kind=kind,
        metadata_json={
            "kind": "lesson_asset",
            "asset_type": kind,
            "lesson_id": lesson.id,
            "course_id": course_id,
        },
        keep_local_working_copy=True,
    )
    # Processors still open a local path; MediaObject points at the configured provider.
    storage_path = stored.local_path or stored.storage_key
    return await upsert_asset(
        db,
        lesson,
        asset_type,
        storage_path,
        media=stored.media,
        original_filename=filename,
        mime_type=stored.mime_type,
        file_size_bytes=stored.size_bytes,
        uploaded_by_user_id=user_id,
    )


def lesson_has_any_asset(lesson: Lesson) -> bool:
    paths = paths_from_lesson(lesson)
    return any(paths.values())


def assets_public_urls(lesson: Lesson) -> dict[str, str | None]:
    """Client-facing URLs for lesson assets (MediaObject-aware)."""
    amap = asset_map_from_lesson(lesson)
    urls: dict[str, str | None] = {}
    for key in ("video", "pdf", "homework", "audio"):
        asset = amap.get(key)
        if asset is not None:
            urls[key] = _asset_client_url(asset)
        else:
            legacy = paths_from_lesson(lesson).get(key)
            urls[key] = public_url(legacy)
    return urls


def _clear_legacy_column(lesson: Lesson, asset_type: LessonAssetType) -> None:
    if asset_type == LessonAssetType.video:
        lesson.video_url = None
    elif asset_type == LessonAssetType.pdf:
        lesson.pdf_path = None
    elif asset_type == LessonAssetType.homework:
        lesson.homework_path = None
    elif asset_type == LessonAssetType.audio:
        lesson.voice_path = None


def _safe_unlink(path: str | None) -> None:
    if not path:
        return
    try:
        file_path = Path(path)
        if file_path.is_file():
            file_path.unlink(missing_ok=True)
    except Exception:
        pass


async def remove_lesson_asset(
    db: AsyncSession,
    lesson: Lesson,
    asset_type: LessonAssetType,
) -> None:
    """Remove asset row, clear legacy column, and delete local working copy if present."""
    amap = asset_map_from_lesson(lesson)
    asset = amap.get(asset_type.value)
    old_path = asset.storage_path if asset else paths_from_lesson(lesson).get(asset_type.value)
    if asset:
        await db.delete(asset)
    _clear_legacy_column(lesson, asset_type)
    _safe_unlink(old_path)
    await db.flush()
