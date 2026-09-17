"""Validate teacher voice samples before AI processing."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.services.voice_service import _find_ffmpeg_executable, _load_audio_mono_16k

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class VoiceValidationResult:
    ok: bool
    duration_seconds: float = 0.0
    error: str | None = None


def _load_audio_array(path: Path):
    import numpy as np

    audio, sample_rate = _load_audio_mono_16k(path)
    duration = len(audio) / sample_rate
    return audio, float(duration), np


def _duration_via_ffprobe(path: Path) -> float | None:
    ffprobe = _find_ffmpeg_executable()
    if not ffprobe:
        return None
    probe = "ffprobe" if ffprobe.endswith("ffmpeg") else ffprobe.replace("ffmpeg", "ffprobe")
    if not Path(probe).exists() and probe == "ffprobe":
        import shutil

        probe = shutil.which("ffprobe")
    if not probe:
        return None
    try:
        out = subprocess.run(
            [
                probe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            return float(out.stdout.strip())
    except Exception as exc:
        logger.debug("ffprobe duration failed: %s", exc)
    return None


def validate_voice_sample(path: str | Path) -> VoiceValidationResult:
    """Check duration, silence, corruption, speech, and basic quality."""
    file_path = Path(path)
    if not file_path.is_file() or file_path.stat().st_size < 1024:
        return VoiceValidationResult(ok=False, error="الملف الصوتي فارغ أو تالف")

    min_seconds = settings.VOICE_SAMPLE_MIN_SECONDS
    max_bytes = settings.MAX_VOICE_SAMPLE_BYTES
    if file_path.stat().st_size > max_bytes:
        return VoiceValidationResult(
            ok=False,
            error=f"حجم الملف كبير جداً (الحد {max_bytes // (1024 * 1024)} ميجابايت)",
        )

    duration = _duration_via_ffprobe(file_path)
    audio = None
    np_mod = None

    try:
        audio, whisper_duration, np_mod = _load_audio_array(file_path)
        duration = duration or whisper_duration
    except Exception as exc:
        logger.warning("Could not decode audio %s: %s", file_path, exc)
        return VoiceValidationResult(ok=False, error="تعذر قراءة الملف الصوتي — قد يكون تالفاً")

    if duration < min_seconds:
        return VoiceValidationResult(
            ok=False,
            duration_seconds=duration,
            error=f"مدة التسجيل {int(duration)} ثانية — الحد الأدنى {min_seconds} ثانية",
        )

    if audio is not None and np_mod is not None:
        peak = float(np_mod.max(np_mod.abs(audio)))
        rms = float(np_mod.sqrt(np_mod.mean(audio**2)))

        if peak < 0.005 or rms < 0.002:
            return VoiceValidationResult(
                ok=False,
                duration_seconds=duration,
                error="التسجيل صامت أو بدون صوت مسموع",
            )

        if peak > 0.99 and rms > 0.3:
            return VoiceValidationResult(
                ok=False,
                duration_seconds=duration,
                error="جودة الصوت منخفضة — يبدو أن هناك تشويشاً أو تشبعاً في التسجيل",
            )

        # Speech activity: enough amplitude variation across the clip
        window = max(1, len(audio) // 20)
        chunks = [audio[i : i + window] for i in range(0, len(audio), window)]
        chunk_rms = [float(np_mod.sqrt(np_mod.mean(c**2))) for c in chunks if len(c)]
        active = sum(1 for v in chunk_rms if v > rms * 0.35)
        if active < max(3, len(chunk_rms) // 5):
            return VoiceValidationResult(
                ok=False,
                duration_seconds=duration,
                error="لم نتعرف على كلام بشري واضح في التسجيل",
            )

    return VoiceValidationResult(ok=True, duration_seconds=duration)
