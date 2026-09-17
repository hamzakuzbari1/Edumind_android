"""ElevenLabs voice cloning and speech synthesis client."""

from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ElevenLabsError(RuntimeError):
    """Raised when ElevenLabs rejects or cannot complete a request."""


@dataclass(frozen=True)
class ElevenLabsVoiceClone:
    voice_id: str
    requires_verification: bool = False


def _base_url() -> str:
    return (settings.ELEVENLABS_BASE_URL or "https://api.elevenlabs.io/v1").rstrip("/")


def _api_key() -> str:
    key = (settings.ELEVENLABS_API_KEY or "").strip()
    if not key:
        raise ElevenLabsError("ELEVENLABS_API_KEY is not configured")
    return key


def _headers(*, accept: str | None = None) -> dict[str, str]:
    headers = {"xi-api-key": _api_key()}
    if accept:
        headers["Accept"] = accept
    return headers


def _timeout() -> httpx.Timeout:
    return httpx.Timeout(float(settings.TTS_REQUEST_TIMEOUT_SECONDS or 120))


async def create_voice_clone(
    sample_path: str | Path,
    *,
    name: str,
    description: str | None = None,
) -> ElevenLabsVoiceClone:
    """Create an ElevenLabs instant voice clone from a local audio file."""

    path = Path(sample_path)
    if not path.is_file():
        raise ElevenLabsError(f"voice sample file not found: {path}")

    mime_type = mimetypes.guess_type(path.name)[0] or "audio/wav"
    data = {"name": name}
    if description:
        data["description"] = description

    try:
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            with path.open("rb") as audio_file:
                response = await client.post(
                    f"{_base_url()}/voices/add",
                    headers=_headers(),
                    data=data,
                    files={"files": (path.name, audio_file, mime_type)},
                )
    except httpx.HTTPError as exc:
        raise ElevenLabsError(f"ElevenLabs voice clone request failed: {exc}") from exc

    if response.status_code >= 400:
        raise ElevenLabsError(_error_message(response, "ElevenLabs voice clone failed"))

    try:
        payload = response.json()
    except ValueError as exc:
        raise ElevenLabsError("ElevenLabs voice clone returned invalid JSON") from exc

    voice_id = str(payload.get("voice_id") or "").strip()
    if not voice_id:
        raise ElevenLabsError("ElevenLabs voice clone response did not include voice_id")

    return ElevenLabsVoiceClone(
        voice_id=voice_id,
        requires_verification=bool(payload.get("requires_verification", False)),
    )


async def delete_voice(voice_id: str | None) -> None:
    """Best-effort cleanup for cloned voices that belong to deleted samples."""

    voice_id = (voice_id or "").strip()
    if not voice_id:
        return

    try:
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            response = await client.delete(
                f"{_base_url()}/voices/{voice_id}",
                headers=_headers(),
            )
        if response.status_code >= 400 and response.status_code != 404:
            logger.warning("ElevenLabs voice delete failed status=%s body=%s", response.status_code, response.text[:300])
    except Exception as exc:
        logger.warning("ElevenLabs voice delete request failed voice_id=%s error=%s", voice_id, exc)


async def synthesize_speech(
    *,
    text: str,
    voice_id: str,
    output_path: Path,
    language: str | None = None,
) -> bool:
    """Synthesize text to an audio file using an existing ElevenLabs voice id."""

    voice_id = (voice_id or "").strip()
    if not voice_id:
        raise ElevenLabsError("ElevenLabs voice_id is required for synthesis")

    body: dict = {
        "text": text,
        "model_id": settings.ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": float(settings.ELEVENLABS_STABILITY),
            "similarity_boost": float(settings.ELEVENLABS_SIMILARITY_BOOST),
            "style": float(settings.ELEVENLABS_STYLE),
            "use_speaker_boost": bool(settings.ELEVENLABS_USE_SPEAKER_BOOST),
        },
    }
    if language:
        body["language_code"] = language

    params = {}
    output_format = (settings.ELEVENLABS_OUTPUT_FORMAT or "").strip()
    if output_format:
        params["output_format"] = output_format

    try:
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            response = await client.post(
                f"{_base_url()}/text-to-speech/{voice_id}",
                headers=_headers(accept=_accept_header(output_format)),
                params=params,
                json=body,
            )
    except httpx.HTTPError as exc:
        raise ElevenLabsError(f"ElevenLabs synthesis request failed: {exc}") from exc

    if response.status_code >= 400:
        raise ElevenLabsError(_error_message(response, "ElevenLabs synthesis failed"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path.exists() and output_path.stat().st_size > 0


def _error_message(response: httpx.Response, fallback: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    detail = None
    if isinstance(payload, dict):
        raw_detail = payload.get("detail") or payload.get("message")
        if isinstance(raw_detail, dict):
            detail = raw_detail.get("message") or raw_detail.get("status")
        elif raw_detail:
            detail = str(raw_detail)

    return f"{fallback}: status={response.status_code} detail={detail or response.text[:300]}"


def _accept_header(output_format: str) -> str:
    fmt = (output_format or "").lower()
    if fmt.startswith("wav"):
        return "audio/wav"
    if fmt.startswith("opus"):
        return "audio/opus"
    if fmt.startswith(("pcm", "ulaw", "alaw")):
        return "application/octet-stream"
    return "audio/mpeg"
