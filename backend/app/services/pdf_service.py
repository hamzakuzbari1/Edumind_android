"""PDF OCR orchestration — Mistral extraction + shared chunking/normalization."""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from pathlib import Path

from app.core.config import get_settings
from app.services.mistral_ocr_service import extract_pdf

logger = logging.getLogger(__name__)
settings = get_settings()


def _text_is_too_short(text: str) -> bool:
    clean = re.sub(r"\[[^\]]+\]", " ", text or "").strip()
    words = re.findall(r"[\w\u0600-\u06FF]+", clean)
    return len(clean) < settings.MIN_EXTRACTED_TEXT_CHARS or len(words) < 20


def _short_text_error() -> ValueError:
    return ValueError(
        "النص المستخرج من PDF قصير جداً. تأكد أن مفتاح OCR مضبوط وأن الملف واضح وقابل للقراءة."
    )


def extract_text_from_pdf(pdf_path: str | Path) -> tuple[str, int, list[dict]]:
    """Return (full_text, page_count, metadata_list per page) via configured OCR provider."""
    raw_text = extract_pdf(pdf_path)
    full_text, page_count, pages_meta = _normalize_pdf_ocr_text(raw_text)
    if _text_is_too_short(full_text):
        raise _short_text_error()
    return full_text, page_count, pages_meta


async def extract_text_from_pdf_async(pdf_path: str | Path) -> tuple[str, int, list[dict]]:
    return await asyncio.to_thread(extract_text_from_pdf, pdf_path)


def _normalize_arabic_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_pdf_ocr_text(text: str) -> tuple[str, int, list[dict]]:
    raw = (text or "").replace("```text", "").replace("```", "").strip()
    raw = re.sub(r"\[page\s+(\d+)\]", r"[PAGE \1]", raw, flags=re.IGNORECASE)
    parts = re.split(r"(?=\[PAGE\s+\d+\])", raw)
    pages: list[tuple[int, str]] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue
        match = re.match(r"\[PAGE\s+(\d+)\]\s*(.*)", part, flags=re.IGNORECASE | re.DOTALL)
        if match:
            page_no = int(match.group(1))
            page_text = _normalize_arabic_text(match.group(2))
        else:
            page_no = len(pages) + 1
            page_text = _normalize_arabic_text(part)
        if page_text:
            pages.append((page_no, page_text))

    if not pages:
        clean = _normalize_arabic_text(raw)
        meta = [{"page": 1, "chars": len(clean)}] if clean else []
        return clean, 1 if clean else 0, meta

    output_parts: list[str] = []
    meta: list[dict] = []
    for page_no, page_text in pages:
        output_parts.append(f"[PAGE {page_no}]\n{page_text}")
        meta.append({"page": page_no, "chars": len(page_text)})
    return "\n\n".join(output_parts).strip(), len(meta), meta


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}".strip() if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) <= chunk_size:
                current = para
            else:
                sentences = re.split(r"(?<=[.!?؟。])\s+", para)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= chunk_size:
                        current = f"{current} {sent}".strip()
                    else:
                        if current:
                            chunks.append(current)
                        current = sent
                if current:
                    chunks.append(current)
                current = ""

    if current:
        chunks.append(current)

    if overlap > 0 and len(chunks) > 1:
        overlapped: list[str] = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:]
            overlapped.append(f"{prev_tail}\n{chunks[i]}".strip())
        chunks = overlapped

    return chunks
