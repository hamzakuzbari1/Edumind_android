"""Message attachment storage (images, PDFs, documents, voice)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.models.conversation import MessageKind

settings = get_settings()

MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024
MAX_VOICE_BYTES = 8 * 1024 * 1024

IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
PDF_MIMES = {"application/pdf"}
DOC_MIMES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
}
VOICE_MIMES = {"audio/webm", "audio/mpeg", "audio/mp3", "audio/ogg", "audio/wav", "audio/x-wav"}


def _infer_kind(mime: str, filename: str) -> MessageKind:
    m = (mime or "").lower().split(";")[0].strip()
    ext = Path(filename or "").suffix.lower()
    if m in IMAGE_MIMES or ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return MessageKind.image
    if m in PDF_MIMES or ext == ".pdf":
        return MessageKind.pdf
    if m in VOICE_MIMES or ext in {".webm", ".mp3", ".ogg", ".wav", ".m4a"}:
        return MessageKind.voice
    if m in DOC_MIMES or ext in {".doc", ".docx", ".xls", ".xlsx", ".txt"}:
        return MessageKind.document
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="نوع الملف غير مدعوم. المسموح: صور، PDF، مستندات، أو رسالة صوتية",
    )


def prepare_message_file(
    *,
    content: bytes,
    filename: str,
    mime_type: str,
    voice_duration_ms: int | None = None,
) -> tuple[MessageKind, str, str]:
    """Validate a message upload without deciding where it is stored."""
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الملف فارغ")

    kind = _infer_kind(mime_type, filename)
    if kind == MessageKind.voice:
        limit = MAX_VOICE_BYTES
    elif kind == MessageKind.pdf:
        limit = settings.MAX_PDF_BYTES
    else:
        limit = MAX_ATTACHMENT_BYTES
    if len(content) > limit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="حجم الملف كبير جداً")

    ext = Path(filename).suffix or {
        MessageKind.image: ".jpg",
        MessageKind.pdf: ".pdf",
        MessageKind.voice: ".webm",
        MessageKind.document: ".bin",
    }.get(kind, ".bin")
    stored_name = filename or f"{kind.value}_{uuid.uuid4().hex}{ext}"
    mime = (mime_type or "").split(";")[0].strip() or "application/octet-stream"
    if kind == MessageKind.voice:
        if ext in {".webm"} or mime in ("application/octet-stream", ""):
            mime = "audio/webm"
        elif ext in {".m4a", ".mp4"}:
            mime = "audio/mp4"
        elif ext == ".ogg":
            mime = "audio/ogg"
    if kind == MessageKind.voice and voice_duration_ms is not None and voice_duration_ms < 0:
        voice_duration_ms = None
    return kind, stored_name, mime


def save_message_file(
    *,
    uploader_id: int,
    thread_id: int,
    content: bytes,
    filename: str,
    mime_type: str,
    voice_duration_ms: int | None = None,
) -> tuple[MessageKind, str, str, str]:
    """Legacy local /uploads storage. New message attachments use MediaObject storage."""
    kind, stored_name, mime = prepare_message_file(
        content=content,
        filename=filename,
        mime_type=mime_type,
        voice_duration_ms=voice_duration_ms,
    )
    ext = Path(stored_name).suffix or {
        MessageKind.image: ".jpg",
        MessageKind.pdf: ".pdf",
        MessageKind.voice: ".webm",
        MessageKind.document: ".bin",
    }.get(kind, ".bin")

    root = Path(settings.UPLOAD_DIR) / "messages" / f"thread_{thread_id}"
    root.mkdir(parents=True, exist_ok=True)
    safe_name = f"{kind.value}_{uploader_id}_{uuid.uuid4().hex}{ext}"
    dest = root / safe_name
    dest.write_bytes(content)
    rel = dest.resolve().relative_to(Path(settings.UPLOAD_DIR).resolve())
    public = "/uploads/" + "/".join(rel.parts)
    return kind, public, stored_name, mime



def preview_label_for_kind(kind: MessageKind | str, name: str | None = None) -> str:
    k = kind.value if hasattr(kind, "value") else str(kind)
    if k == MessageKind.image.value:
        return "📷 صورة"
    if k == MessageKind.pdf.value:
        return "📄 PDF"
    if k == MessageKind.document.value:
        return f"📎 {name or 'مستند'}"
    if k == MessageKind.voice.value:
        return "🎤 رسالة صوتية"
    return name or ""
