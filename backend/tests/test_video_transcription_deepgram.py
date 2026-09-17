"""Tests for uploaded lesson-video Deepgram Nova-3 transcription (mocked)."""

from __future__ import annotations

import logging
import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.video_transcription.deepgram import DeepgramTranscriptionProvider
from app.services.video_transcription.errors import (
    CATEGORY_EMPTY_TRANSCRIPT,
    CATEGORY_HTTP_429,
    CATEGORY_HTTP_5XX,
    CATEGORY_INVALID_API_KEY,
    CATEGORY_MISSING_API_KEY,
    CATEGORY_TIMEOUT,
    VideoTranscriptionError,
)
from app.services.video_transcription.factory import get_video_transcription_provider
from app.services.video_transcription.language import (
    map_locale_to_deepgram_language,
    resolve_video_transcription_language,
)
from app.services.video_transcription.types import TranscriptResult


FAKE_API_KEY = "dg_test_secret_key_never_log_me"


def _write_silent_wav(path: Path, *, seconds: float = 0.2) -> None:
    rate = 16000
    frames = int(rate * seconds)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x00" * frames)


def _deepgram_payload(
    transcript: str = "مرحبا. This is Newton's law.",
    *,
    with_paragraphs: bool = True,
) -> dict:
    alternative: dict = {
        "transcript": transcript,
        "confidence": 0.95,
    }
    if with_paragraphs:
        alternative["paragraphs"] = {
            "transcript": transcript,
            "paragraphs": [
                {
                    "sentences": [
                        {"text": "مرحبا.", "start": 0.0, "end": 0.5},
                        {"text": "This is Newton's law.", "start": 0.5, "end": 2.0},
                    ],
                    "start": 0.0,
                    "end": 2.0,
                }
            ],
        }
    return {
        "metadata": {"duration": 2.0, "model_info": {"name": "nova-3"}},
        "results": {"channels": [{"alternatives": [alternative]}]},
    }


@pytest.fixture
def wav_path(tmp_path: Path) -> Path:
    path = tmp_path / "lesson.wav"
    _write_silent_wav(path)
    return path


class TestLanguageMapping:
    def test_arabic_syrian_maps_to_ar_sy(self):
        assert map_locale_to_deepgram_language("ar-SY") == "ar-SY"
        assert map_locale_to_deepgram_language("ar_sy") == "ar-SY"
        assert resolve_video_transcription_language(locale="ar-SY") == "ar-SY"

    def test_english_maps_to_en(self):
        assert map_locale_to_deepgram_language("en") == "en"
        assert resolve_video_transcription_language(language_hint="en-US") == "en"
        assert resolve_video_transcription_language(subject="English") == "en"

    def test_default_config_language(self):
        with patch("app.services.video_transcription.language.get_settings") as gs:
            settings = MagicMock()
            settings.DEEPGRAM_STT_LANGUAGE = "ar-SY"
            settings.LESSON_VIDEO_WHISPER_LANGUAGE = "ar"
            gs.return_value = settings
            assert resolve_video_transcription_language() == "ar-SY"


class TestFactory:
    def test_selects_deepgram_when_configured(self):
        with patch("app.services.video_transcription.factory.get_settings") as gs:
            settings = MagicMock()
            settings.VIDEO_TRANSCRIPTION_PROVIDER = "deepgram"
            gs.return_value = settings
            provider = get_video_transcription_provider()
            assert provider.name == "deepgram"
            assert isinstance(provider, DeepgramTranscriptionProvider)

    def test_selects_whisper_rollback(self):
        with patch("app.services.video_transcription.factory.get_settings") as gs:
            settings = MagicMock()
            settings.VIDEO_TRANSCRIPTION_PROVIDER = "whisper"
            gs.return_value = settings
            assert get_video_transcription_provider().name == "whisper"


class TestDeepgramProvider:
    @pytest.mark.asyncio
    async def test_model_is_nova_3_and_maps_contract(self, wav_path: Path):
        captured: dict = {}

        def fake_post(url, **kwargs):
            captured["url"] = url
            captured["params"] = dict(kwargs.get("params") or [])
            captured["headers"] = kwargs.get("headers") or {}
            captured["content_len"] = len(kwargs.get("content") or b"")
            return httpx.Response(200, json=_deepgram_payload())

        with (
            patch("app.services.video_transcription.deepgram.get_settings") as gs,
            patch("app.services.video_transcription.deepgram.httpx.post", side_effect=fake_post),
        ):
            settings = MagicMock()
            settings.DEEPGRAM_API_KEY = FAKE_API_KEY
            settings.DEEPGRAM_STT_MODEL = "nova-3"
            settings.DEEPGRAM_STT_TIMEOUT_SECONDS = 300
            settings.DEEPGRAM_STT_SMART_FORMAT = True
            gs.return_value = settings

            result = await DeepgramTranscriptionProvider().transcribe(
                wav_path, language="ar-SY", mime_type="audio/wav"
            )

        assert result.provider == "deepgram"
        assert result.model == "nova-3"
        assert result.language == "ar-SY"
        assert "مرحبا" in result.text
        assert "Newton" in result.text
        assert result.segments
        assert captured["params"]["model"] == "nova-3"
        assert captured["params"]["language"] == "ar-SY"
        assert captured["params"]["smart_format"] == "true"
        assert captured["params"]["punctuate"] == "true"
        assert captured["params"]["paragraphs"] == "true"
        assert FAKE_API_KEY not in result.text
        assert "results" not in result.text

    @pytest.mark.asyncio
    async def test_punctuation_and_formatting_preserved(self, wav_path: Path):
        payload = _deepgram_payload("Hello, world! هذا درس.")

        with (
            patch("app.services.video_transcription.deepgram.get_settings") as gs,
            patch(
                "app.services.video_transcription.deepgram.httpx.post",
                return_value=httpx.Response(200, json=payload),
            ),
        ):
            settings = MagicMock()
            settings.DEEPGRAM_API_KEY = FAKE_API_KEY
            settings.DEEPGRAM_STT_MODEL = "nova-3"
            settings.DEEPGRAM_STT_TIMEOUT_SECONDS = 30
            settings.DEEPGRAM_STT_SMART_FORMAT = True
            gs.return_value = settings
            result = await DeepgramTranscriptionProvider().transcribe(wav_path, language="ar")

        assert "Hello, world!" in result.text
        assert "هذا درس." in result.text

    @pytest.mark.asyncio
    async def test_arabic_english_educational_sample_mapping(self, wav_path: Path):
        text = "اليوم نشرح photosynthesis و Newton's laws في الصف."
        with (
            patch("app.services.video_transcription.deepgram.get_settings") as gs,
            patch(
                "app.services.video_transcription.deepgram.httpx.post",
                return_value=httpx.Response(200, json=_deepgram_payload(text)),
            ),
        ):
            settings = MagicMock()
            settings.DEEPGRAM_API_KEY = FAKE_API_KEY
            settings.DEEPGRAM_STT_MODEL = "nova-3"
            settings.DEEPGRAM_STT_TIMEOUT_SECONDS = 30
            settings.DEEPGRAM_STT_SMART_FORMAT = True
            gs.return_value = settings
            result = await DeepgramTranscriptionProvider().transcribe(
                wav_path, language="ar-SY", keyterms=["photosynthesis", "Newton"]
            )
        assert "photosynthesis" in result.text
        assert "Newton" in result.text
        assert "اليوم" in result.text

    @pytest.mark.asyncio
    async def test_empty_transcript_rejected(self, wav_path: Path):
        with (
            patch("app.services.video_transcription.deepgram.get_settings") as gs,
            patch(
                "app.services.video_transcription.deepgram.httpx.post",
                return_value=httpx.Response(
                    200, json=_deepgram_payload("", with_paragraphs=False)
                ),
            ),
        ):
            settings = MagicMock()
            settings.DEEPGRAM_API_KEY = FAKE_API_KEY
            settings.DEEPGRAM_STT_MODEL = "nova-3"
            settings.DEEPGRAM_STT_TIMEOUT_SECONDS = 30
            settings.DEEPGRAM_STT_SMART_FORMAT = True
            gs.return_value = settings
            with pytest.raises(VideoTranscriptionError) as exc:
                await DeepgramTranscriptionProvider().transcribe(wav_path, language="ar-SY")
        assert exc.value.category == CATEGORY_EMPTY_TRANSCRIPT

    @pytest.mark.asyncio
    async def test_missing_api_key_fails_clearly(self, wav_path: Path):
        with patch("app.services.video_transcription.deepgram.get_settings") as gs:
            settings = MagicMock()
            settings.DEEPGRAM_API_KEY = ""
            settings.DEEPGRAM_STT_MODEL = "nova-3"
            settings.DEEPGRAM_STT_TIMEOUT_SECONDS = 30
            settings.DEEPGRAM_STT_SMART_FORMAT = True
            gs.return_value = settings
            with pytest.raises(VideoTranscriptionError) as exc:
                await DeepgramTranscriptionProvider().transcribe(wav_path, language="ar-SY")
        assert exc.value.category == CATEGORY_MISSING_API_KEY
        assert FAKE_API_KEY not in str(exc.value)

    @pytest.mark.asyncio
    async def test_401_no_retry(self, wav_path: Path):
        calls = {"n": 0}

        def fake_post(*_a, **_k):
            calls["n"] += 1
            return httpx.Response(401, text="unauthorized")

        with (
            patch("app.services.video_transcription.deepgram.get_settings") as gs,
            patch("app.services.video_transcription.deepgram.httpx.post", side_effect=fake_post),
            patch("app.services.video_transcription.deepgram.time.sleep") as sleep,
        ):
            settings = MagicMock()
            settings.DEEPGRAM_API_KEY = FAKE_API_KEY
            settings.DEEPGRAM_STT_MODEL = "nova-3"
            settings.DEEPGRAM_STT_TIMEOUT_SECONDS = 30
            settings.DEEPGRAM_STT_SMART_FORMAT = True
            gs.return_value = settings
            with pytest.raises(VideoTranscriptionError) as exc:
                await DeepgramTranscriptionProvider().transcribe(wav_path, language="ar-SY")
        assert exc.value.category == CATEGORY_INVALID_API_KEY
        assert calls["n"] == 1
        sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_429_retried_with_limit(self, wav_path: Path):
        calls = {"n": 0}

        def fake_post(*_a, **_k):
            calls["n"] += 1
            return httpx.Response(429, text="rate limit")

        with (
            patch("app.services.video_transcription.deepgram.get_settings") as gs,
            patch("app.services.video_transcription.deepgram.httpx.post", side_effect=fake_post),
            patch("app.services.video_transcription.deepgram.time.sleep"),
        ):
            settings = MagicMock()
            settings.DEEPGRAM_API_KEY = FAKE_API_KEY
            settings.DEEPGRAM_STT_MODEL = "nova-3"
            settings.DEEPGRAM_STT_TIMEOUT_SECONDS = 30
            settings.DEEPGRAM_STT_SMART_FORMAT = True
            gs.return_value = settings
            with pytest.raises(VideoTranscriptionError) as exc:
                await DeepgramTranscriptionProvider().transcribe(wav_path, language="ar-SY")
        assert exc.value.category == CATEGORY_HTTP_429
        assert calls["n"] == 3

    @pytest.mark.asyncio
    async def test_5xx_retried_with_limit(self, wav_path: Path):
        calls = {"n": 0}

        def fake_post(*_a, **_k):
            calls["n"] += 1
            return httpx.Response(503, text="unavailable")

        with (
            patch("app.services.video_transcription.deepgram.get_settings") as gs,
            patch("app.services.video_transcription.deepgram.httpx.post", side_effect=fake_post),
            patch("app.services.video_transcription.deepgram.time.sleep"),
        ):
            settings = MagicMock()
            settings.DEEPGRAM_API_KEY = FAKE_API_KEY
            settings.DEEPGRAM_STT_MODEL = "nova-3"
            settings.DEEPGRAM_STT_TIMEOUT_SECONDS = 30
            settings.DEEPGRAM_STT_SMART_FORMAT = True
            gs.return_value = settings
            with pytest.raises(VideoTranscriptionError) as exc:
                await DeepgramTranscriptionProvider().transcribe(wav_path, language="ar-SY")
        assert exc.value.category == CATEGORY_HTTP_5XX
        assert calls["n"] == 3

    @pytest.mark.asyncio
    async def test_timeout_handled(self, wav_path: Path):
        with (
            patch("app.services.video_transcription.deepgram.get_settings") as gs,
            patch(
                "app.services.video_transcription.deepgram.httpx.post",
                side_effect=httpx.TimeoutException("timeout"),
            ),
            patch("app.services.video_transcription.deepgram.time.sleep"),
        ):
            settings = MagicMock()
            settings.DEEPGRAM_API_KEY = FAKE_API_KEY
            settings.DEEPGRAM_STT_MODEL = "nova-3"
            settings.DEEPGRAM_STT_TIMEOUT_SECONDS = 1
            settings.DEEPGRAM_STT_SMART_FORMAT = True
            gs.return_value = settings
            with pytest.raises(VideoTranscriptionError) as exc:
                await DeepgramTranscriptionProvider().transcribe(wav_path, language="ar-SY")
        assert exc.value.category == CATEGORY_TIMEOUT


class TestVideoFlowOrchestration:
    @pytest.mark.asyncio
    async def test_whisper_not_called_in_deepgram_flow(self, tmp_path: Path):
        from app.services import voice_service

        video = tmp_path / "lesson.mp4"
        video.write_bytes(b"\x00\x00\x00\x18ftypmp42")
        wav = tmp_path / "extracted.wav"
        _write_silent_wav(wav)

        deepgram = MagicMock()
        deepgram.name = "deepgram"
        deepgram.transcribe = AsyncMock(
            return_value=TranscriptResult(
                text="نص الدرس",
                provider="deepgram",
                model="nova-3",
                language="ar-SY",
            )
        )
        whisper = MagicMock()
        whisper.name = "whisper"
        whisper.transcribe = AsyncMock()

        def factory(name=None):
            if (name or "deepgram") == "whisper":
                return whisper
            return deepgram

        with (
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_PROVIDER", "deepgram"),
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_ALLOW_WHISPER_FALLBACK", False),
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_ALLOW_GEMINI_FALLBACK", False),
            patch.object(voice_service, "_extract_video_to_wav", return_value=wav),
            patch(
                "app.services.video_transcription.factory.get_video_transcription_provider",
                side_effect=factory,
            ),
            patch.object(voice_service, "_transcribe_lesson_video_whisper_sync") as whisper_sync,
            patch.object(voice_service, "_transcribe_video_with_gemini", new_callable=AsyncMock) as gemini,
        ):
            text = await voice_service.transcribe_lesson_video(video)

        assert text == "نص الدرس"
        whisper.transcribe.assert_not_called()
        whisper_sync.assert_not_called()
        gemini.assert_not_called()

    @pytest.mark.asyncio
    async def test_temp_audio_removed_on_success(self, tmp_path: Path):
        from app.services import voice_service

        video = tmp_path / "ok.mp4"
        video.write_bytes(b"fake")
        wav = tmp_path / "temp_ok.wav"
        _write_silent_wav(wav)

        deepgram = MagicMock()
        deepgram.name = "deepgram"
        deepgram.transcribe = AsyncMock(
            return_value=TranscriptResult(
                text="ok", provider="deepgram", model="nova-3", language="ar-SY"
            )
        )

        with (
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_PROVIDER", "deepgram"),
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_ALLOW_WHISPER_FALLBACK", False),
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_ALLOW_GEMINI_FALLBACK", False),
            patch.object(voice_service, "_extract_video_to_wav", return_value=wav),
            patch(
                "app.services.video_transcription.factory.get_video_transcription_provider",
                return_value=deepgram,
            ),
        ):
            await voice_service.transcribe_lesson_video(video)

        assert not wav.exists()

    @pytest.mark.asyncio
    async def test_temp_audio_removed_on_failure(self, tmp_path: Path):
        from app.services import voice_service

        video = tmp_path / "fail.mp4"
        video.write_bytes(b"fake")
        wav = tmp_path / "temp_fail.wav"
        _write_silent_wav(wav)

        deepgram = MagicMock()
        deepgram.name = "deepgram"
        deepgram.transcribe = AsyncMock(
            side_effect=VideoTranscriptionError(
                "fail", category=CATEGORY_HTTP_5XX, provider="deepgram"
            )
        )

        with (
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_PROVIDER", "deepgram"),
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_ALLOW_WHISPER_FALLBACK", False),
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_ALLOW_GEMINI_FALLBACK", False),
            patch.object(voice_service, "_extract_video_to_wav", return_value=wav),
            patch(
                "app.services.video_transcription.factory.get_video_transcription_provider",
                return_value=deepgram,
            ),
        ):
            with pytest.raises(VideoTranscriptionError):
                await voice_service.transcribe_lesson_video(video)

        assert not wav.exists()

    @pytest.mark.asyncio
    async def test_api_key_never_in_logs_or_exception(self, wav_path: Path, caplog):
        with (
            patch("app.services.video_transcription.deepgram.get_settings") as gs,
            patch(
                "app.services.video_transcription.deepgram.httpx.post",
                return_value=httpx.Response(401, text=f"bad key {FAKE_API_KEY}"),
            ),
            caplog.at_level(logging.WARNING),
        ):
            settings = MagicMock()
            settings.DEEPGRAM_API_KEY = FAKE_API_KEY
            settings.DEEPGRAM_STT_MODEL = "nova-3"
            settings.DEEPGRAM_STT_TIMEOUT_SECONDS = 30
            settings.DEEPGRAM_STT_SMART_FORMAT = True
            gs.return_value = settings
            with pytest.raises(VideoTranscriptionError) as exc:
                await DeepgramTranscriptionProvider().transcribe(wav_path, language="ar-SY")

        assert FAKE_API_KEY not in str(exc.value)
        assert FAKE_API_KEY not in exc.value.user_message
        joined = "\n".join(r.getMessage() for r in caplog.records)
        assert FAKE_API_KEY not in joined
        assert "Authorization" not in joined

    @pytest.mark.asyncio
    async def test_no_raw_provider_response_leak(self, wav_path: Path):
        payload = _deepgram_payload("safe text")
        with (
            patch("app.services.video_transcription.deepgram.get_settings") as gs,
            patch(
                "app.services.video_transcription.deepgram.httpx.post",
                return_value=httpx.Response(200, json=payload),
            ),
        ):
            settings = MagicMock()
            settings.DEEPGRAM_API_KEY = FAKE_API_KEY
            settings.DEEPGRAM_STT_MODEL = "nova-3"
            settings.DEEPGRAM_STT_TIMEOUT_SECONDS = 30
            settings.DEEPGRAM_STT_SMART_FORMAT = True
            gs.return_value = settings
            result = await DeepgramTranscriptionProvider().transcribe(wav_path, language="ar-SY")

        dumped = repr(result)
        assert "channels" not in dumped
        assert "alternatives" not in dumped
        assert result.text == "safe text"

    @pytest.mark.asyncio
    async def test_frontend_contract_remains_string(self, tmp_path: Path):
        """lesson_processor expects a plain string from transcribe_lesson_video."""
        from app.services import voice_service

        video = tmp_path / "c.mp4"
        video.write_bytes(b"x")
        wav = tmp_path / "c.wav"
        _write_silent_wav(wav)
        deepgram = MagicMock()
        deepgram.name = "deepgram"
        deepgram.transcribe = AsyncMock(
            return_value=TranscriptResult(
                text="عقد متوافق", provider="deepgram", model="nova-3", language="ar-SY"
            )
        )
        with (
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_PROVIDER", "deepgram"),
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_ALLOW_WHISPER_FALLBACK", False),
            patch.object(voice_service.settings, "VIDEO_TRANSCRIPTION_ALLOW_GEMINI_FALLBACK", False),
            patch.object(voice_service, "_extract_video_to_wav", return_value=wav),
            patch(
                "app.services.video_transcription.factory.get_video_transcription_provider",
                return_value=deepgram,
            ),
        ):
            out = await voice_service.transcribe_lesson_video(video)
        assert isinstance(out, str)
        assert out == "عقد متوافق"


class TestUnrelatedWhisperFlowsUntouched:
    def test_transcribe_audio_still_uses_whisper_path(self):
        from app.services import voice_service
        import inspect

        src = inspect.getsource(voice_service.transcribe_audio)
        assert "ENABLE_WHISPER" in src
        assert "_transcribe_with_whisper_sync" in src
        assert "DeepgramTranscriptionProvider" not in src
        assert "video_transcription" not in src

    def test_student_chat_stt_unchanged_entry(self):
        from app.services import student_chat_stt_service
        import inspect

        src = inspect.getsource(student_chat_stt_service.transcribe_student_chat_audio)
        assert "Deepgram" in src or "deepgram" in src
        assert "VIDEO_TRANSCRIPTION_PROVIDER" not in src
