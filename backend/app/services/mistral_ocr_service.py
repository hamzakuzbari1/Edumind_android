"""Mistral OCR provider — PDF/image text extraction via Mistral Document AI."""



from __future__ import annotations



import base64

import logging

from pathlib import Path



import httpx



from app.core.config import get_settings



logger = logging.getLogger(__name__)

settings = get_settings()



MISTRAL_OCR_URL = "https://api.mistral.ai/v1/ocr"

MISTRAL_OCR_TIMEOUT_SECONDS = 600





def extract_pdf(path: str | Path) -> str:

    pdf_path = Path(path)

    if not pdf_path.exists():

        raise FileNotFoundError(str(pdf_path))

    data = pdf_path.read_bytes()

    return extract_document_bytes(data, "application/pdf")





def extract_document_bytes(data: bytes, mime_type: str) -> str:

    if not settings.MISTRAL_API_KEY:

        raise ValueError("MISTRAL_API_KEY is required for Mistral OCR")



    mime = _normalize_mime(mime_type, data)

    b64 = base64.b64encode(data).decode("ascii")



    if mime == "application/pdf":

        document = {

            "type": "document_url",

            "document_url": f"data:application/pdf;base64,{b64}",

        }

    else:

        document = {

            "type": "image_url",

            "image_url": f"data:{mime};base64,{b64}",

        }



    payload = {

        "model": (settings.MISTRAL_OCR_MODEL or "mistral-ocr-latest").strip(),

        "document": document,

    }



    max_attempts = 3

    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):

        try:

            with httpx.Client(timeout=MISTRAL_OCR_TIMEOUT_SECONDS) as client:

                response = client.post(

                    MISTRAL_OCR_URL,

                    headers={

                        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",

                        "Content-Type": "application/json",

                    },

                    json=payload,

                )

                response.raise_for_status()

                body = response.json()

            text = _pages_to_marked_text(body.get("pages") or [])

            logger.info(

                "Mistral OCR extracted %s chars (%s pages) model=%s",

                len(text),

                len(body.get("pages") or []),

                payload["model"],

            )

            return text

        except Exception as exc:

            last_error = exc

            if attempt >= max_attempts:

                logger.warning("Mistral OCR failed after %s attempts: %s", attempt, exc)

                raise

            logger.info("Mistral OCR attempt %s failed, retrying: %s", attempt, exc)



    if last_error:

        raise last_error

    return ""





def _pages_to_marked_text(pages: list) -> str:

    """Preserve page order and emit [PAGE N] markers compatible with lesson normalization."""

    ordered = sorted(pages, key=lambda page: int(page.get("index", 0)))

    parts: list[str] = []

    for page in ordered:

        markdown = (page.get("markdown") or "").strip()

        if not markdown:

            continue

        page_no = int(page.get("index", len(parts))) + 1

        parts.append(f"[PAGE {page_no}]\n{markdown}")

    return "\n\n".join(parts).strip()





def _normalize_mime(mime_type: str, data: bytes) -> str:

    mime = (mime_type or "").strip().lower()

    if mime == "application/pdf" or data[:4] == b"%PDF":

        return "application/pdf"

    if mime in ("image/jpeg", "image/jpg", "image/png", "image/webp"):

        return "image/jpeg" if mime == "image/jpg" else mime

    return mime or "image/jpeg"
