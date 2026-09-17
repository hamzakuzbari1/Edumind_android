"""MIME / size validation primitives for future upload flows (A6.0)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import get_settings

# Shared allow-lists (upload endpoints can compose these).
IMAGE_MIMES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})
PDF_MIMES = frozenset({"application/pdf"})
AUDIO_MIMES = frozenset(
    {
        "audio/webm",
        "audio/mpeg",
        "audio/mp3",
        "audio/ogg",
        "audio/wav",
        "audio/x-wav",
        "audio/mp4",
        "audio/m4a",
    }
)
VIDEO_MIMES = frozenset(
    {
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "video/x-msvideo",
    }
)
DOCUMENT_MIMES = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
    }
)


@dataclass(frozen=True)
class MediaValidationResult:
    mime_type: str
    size_bytes: int
    extension: str


def normalize_mime(mime_type: str | None) -> str:
    return (mime_type or "").lower().split(";")[0].strip()


def extension_of(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


def validate_upload_bytes(
    *,
    content: bytes,
    filename: str,
    mime_type: str | None,
    allowed_mimes: frozenset[str],
    max_bytes: int,
    empty_detail: str = "الملف فارغ",
    mime_detail: str = "نوع الملف غير مدعوم",
    size_detail: str = "حجم الملف كبير جداً",
) -> MediaValidationResult:
    """Shared reject-empty / MIME / size gate for later upload wiring."""
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=empty_detail)

    mime = normalize_mime(mime_type)
    ext = extension_of(filename)
    if mime and mime not in allowed_mimes:
        # Allow octet-stream when extension maps to an allowed family via caller list.
        if mime != "application/octet-stream":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=mime_detail)

    if len(content) > max_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=size_detail)

    return MediaValidationResult(
        mime_type=mime or "application/octet-stream",
        size_bytes=len(content),
        extension=ext,
    )


def default_max_bytes_for_mime(mime_type: str | None) -> int:
    settings = get_settings()
    mime = normalize_mime(mime_type)
    if mime in PDF_MIMES or mime in DOCUMENT_MIMES:
        return int(settings.MAX_PDF_BYTES)
    if mime in AUDIO_MIMES:
        return int(settings.MAX_AUDIO_BYTES)
    if mime in VIDEO_MIMES:
        return int(getattr(settings, "MAX_VIDEO_BYTES", settings.MAX_PDF_BYTES))
    return 15 * 1024 * 1024
