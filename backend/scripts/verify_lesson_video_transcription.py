"""Verify lesson video transcription (Deepgram Nova-3 default).

Usage (from backend/):
    python scripts/verify_lesson_video_transcription.py
    python scripts/verify_lesson_video_transcription.py --benchmark path/to/video.mp4
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import sys
import tempfile
import time
import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _static_checks() -> dict[str, bool]:
    from app.core.config import get_settings
    from app.services import voice_service
    from app.services.video_transcription.factory import get_video_transcription_provider

    settings = get_settings()
    vs = inspect.getsource(voice_service)
    lp_path = Path(__file__).resolve().parents[1] / "app" / "services" / "lesson_processor.py"
    lp = lp_path.read_text(encoding="utf-8")
    tasks_path = Path(__file__).resolve().parents[1] / "app" / "services" / "lesson_processing_tasks.py"
    tasks_src = tasks_path.read_text(encoding="utf-8")

    audio_fn = inspect.getsource(voice_service._transcribe_with_whisper_sync)
    gemini_fn = inspect.getsource(voice_service._transcribe_video_with_gemini)
    lesson_video_fn = inspect.getsource(voice_service.transcribe_lesson_video)
    gemini_fallback_fn = inspect.getsource(voice_service._try_gemini_video_fallback)

    default_provider = get_video_transcription_provider(
        settings.VIDEO_TRANSCRIPTION_PROVIDER or "deepgram"
    )

    return {
        "lesson_processor_uses_transcribe_lesson_video": "transcribe_lesson_video" in lp
        and "transcribe_audio(video_path" not in lp,
        "transcribe_lesson_video_exists": hasattr(voice_service, "transcribe_lesson_video"),
        "ffmpeg_extract_present": "_extract_video_to_wav" in vs,
        "structured_logging_present": "_log_video_transcription" in vs
        and "VideoTranscriptionResult" in vs,
        "default_provider_is_deepgram": default_provider.name == "deepgram"
        or (settings.VIDEO_TRANSCRIPTION_PROVIDER or "").lower() == "deepgram",
        "video_provider_config_present": hasattr(settings, "VIDEO_TRANSCRIPTION_PROVIDER"),
        "deepgram_model_nova3": (settings.DEEPGRAM_STT_MODEL or "") == "nova-3",
        "no_small_en_in_lesson_video": "small.en" not in vs.split("async def transcribe_audio")[0],
        "transcribe_audio_unchanged_arabic": 'language="ar"' in audio_fn,
        "gemini_active_wait": "ACTIVE" in gemini_fn and "get_file" in gemini_fn,
        "gemini_timeout_config": str(settings.LESSON_VIDEO_GEMINI_TIMEOUT_SECONDS) == "600"
        and "LESSON_VIDEO_GEMINI_TIMEOUT_SECONDS" in gemini_fallback_fn,
        "arabic_gemini_video_prompt": "بالعربية" in voice_service.GEMINI_TRANSCRIBE_VIDEO_PROMPT,
        "stale_job_recovery_present": "_recover_stale_lesson_job" in tasks_src
        and "STALE_JOB_SECONDS" in tasks_src,
        "whisper_language_config_ar": settings.LESSON_VIDEO_WHISPER_LANGUAGE == "ar",
        "turbo_maps_to_large_v3_turbo": voice_service._FASTER_WHISPER_MODEL_ALIASES.get("turbo")
        == "large-v3-turbo",
        "no_silent_whisper_fallback_default": settings.VIDEO_TRANSCRIPTION_ALLOW_WHISPER_FALLBACK
        is False,
        "deepgram_wired_in_lesson_video": "get_video_transcription_provider" in lesson_video_fn,
    }


async def _flow_mock_checks() -> dict[str, bool]:
    import os

    from app.services import voice_service
    from app.services.video_transcription.types import TranscriptResult

    fd, video_name = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    video_path = Path(video_name)
    wav_fd, wav_name = tempfile.mkstemp(suffix=".wav")
    os.close(wav_fd)
    wav_path = Path(wav_name)
    try:
        video_path.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00")
        with wave.open(str(wav_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 1600)

        deepgram = MagicMock()
        deepgram.name = "deepgram"
        deepgram.transcribe = AsyncMock(
            return_value=TranscriptResult(
                text="مرحبا بالطلاب",
                provider="deepgram",
                model="nova-3",
                language="ar-SY",
            )
        )
        whisper = MagicMock()
        whisper.name = "whisper"
        whisper.transcribe = AsyncMock()

        def factory(name=None):
            chosen = (name or "deepgram").lower()
            return whisper if chosen == "whisper" else deepgram

        with (
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_PROVIDER", "deepgram"),
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_ALLOW_WHISPER_FALLBACK", False),
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_ALLOW_GEMINI_FALLBACK", False),
            patch.object(voice_service, "_extract_video_to_wav", return_value=wav_path),
            patch(
                "app.services.video_transcription.factory.get_video_transcription_provider",
                side_effect=factory,
            ),
            patch.object(
                voice_service,
                "_transcribe_video_with_gemini",
                new_callable=AsyncMock,
            ) as gemini_mock,
        ):
            text = await voice_service.transcribe_lesson_video(video_path)
            deepgram_ok = text == "مرحبا بالطلاب" and deepgram.transcribe.called
            whisper_not_called = not whisper.transcribe.called
            gemini_not_called = not gemini_mock.called

        return {
            "deepgram_success_skips_whisper_and_gemini": deepgram_ok
            and whisper_not_called
            and gemini_not_called,
        }
    finally:
        video_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)


def _make_silent_wav(path: Path, *, seconds: float = 1.0, sample_rate: int = 16000) -> None:
    n_frames = int(sample_rate * seconds)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)


async def _benchmark(video_path: Path | None) -> dict:
    import os

    from app.services import voice_service

    if video_path and video_path.exists():
        started = time.perf_counter()
        text = await voice_service.transcribe_lesson_video(video_path)
        elapsed = time.perf_counter() - started
        return {
            "mode": "video_file",
            "path": str(video_path),
            "duration_s": round(elapsed, 2),
            "chars": len(text),
            "preview": text[:120],
        }

    return {
        "mode": "skipped",
        "note": "Pass --benchmark path/to/video.mp4 to time the configured provider.",
    }


def _print_results(title: str, results: dict[str, bool | str | float | int | None]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    for key, value in results.items():
        mark = "PASS" if value is True else ("FAIL" if value is False else "INFO")
        print(f"  [{mark}] {key}: {value}")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=None, help="Optional lesson video for timing")
    args = parser.parse_args()

    print("verify_lesson_video_transcription — Deepgram Nova-3 video STT")

    static = _static_checks()
    _print_results("Static checks", static)

    flow = await _flow_mock_checks()
    _print_results("Flow checks (mocked)", flow)

    benchmark = (
        await _benchmark(args.benchmark)
        if args.benchmark
        else {"mode": "skipped", "note": "Pass --benchmark path/to/video.mp4 to load and time the model."}
    )
    _print_results("Benchmark", benchmark)

    all_bool = {**static, **flow}
    failed = [k for k, v in all_bool.items() if v is False]
    if failed:
        print(f"\nFAILED ({len(failed)}): {', '.join(failed)}")
        return 1

    print(f"\nAll {len(all_bool)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
