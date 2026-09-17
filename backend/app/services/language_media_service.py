"""Upload student speaking audio for language learning (placement + practice)."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.media import MediaObject, StorageProvider
from app.services.media_storage_service import register_media_object

settings = get_settings()


async def upload_student_speaking(
    db: AsyncSession,
    *,
    student_id: int,
    subfolder: str,
    filename_hint: str,
    file: UploadFile,
) -> MediaObject:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The audio file is empty")
    ext = Path(file.filename or "speech.webm").suffix or ".webm"
    upload_dir = Path(settings.UPLOAD_DIR) / f"student_{student_id}" / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{filename_hint}{ext}"
    dest.write_bytes(data)

    rel = dest.resolve().relative_to(Path(settings.UPLOAD_DIR).resolve())
    storage_key = "/".join(rel.parts)
    media = await register_media_object(
        db,
        storage_path="uploads/" + storage_key,
        mime_type=file.content_type or "audio/webm",
        file_size_bytes=len(data),
        original_filename=file.filename or "speech.webm",
        uploaded_by_user_id=student_id,
        storage_provider=StorageProvider.local.value,
        storage_key=storage_key,
    )
    media.public_url = "/uploads/" + storage_key
    return media
